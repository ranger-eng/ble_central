import paramiko
import subprocess
import time
import threading
import pandas as pd
import json
import os
import calendar
import matplotlib.pyplot as plt
import matplotlib as mpl
import mpl_ascii


REMOTE_HOST="192.168.0.100"
REMOTE_UN="ranger"
REMOTE_DIR="/mnt/nosferatu/ranger-storage/records/garden"
DATE_FMT = "%Y%m%d%H%M%S"

def toDateStr(timeStmp):
    return time.strftime(DATE_FMT, time.localtime(timeStmp))

def toEpochInt(dateStr):
    return time.mktime(time.strptime(dateStr, DATE_FMT))

def daysToEpochTime(numDays: int):
    epochTime = numDays*60*60*24
    return epochTime

def rightNow():
    return toDateStr(time.time())

def daysAgo(dayz: int):
    return toDateStr(time.time() - daysToEpochTime(dayz))

class Record:
 
    dataFrame = None
    latestDataFrame = None
    unitsDict = None

    def __init__(self):
        self.dataFrame = None
        self.scriptDir = os.path.dirname(os.path.abspath(__file__))
        self.outRecordsDir = os.path.join(self.scriptDir, "outRecords")
        self.inRecordsDir = os.path.join(self.scriptDir, "inRecords")

    def setupPlots(self, width=250, height=50):
        mpl.use("module://mpl_ascii")

        mpl_ascii.AXES_WIDTH=width
        mpl_ascii.AXES_HEIGHT=height


    def plotTemps(self, width=250, height=50):
        if self.dataFrame is None:
            return

        self.setupPlots(width, height)

        self.dataFrame.plot(kind='line', 
            title="Temp Plots",
            ylabel="Temp F",
            xlabel="Day/Month/Year Hour:Min:Sec",
            x='timestamp', 
            ylim=(-20,110), 
            y=['soil2_temp', 'soil1_temp'])

        plt.show()

    def plotPercents(self, width=250, height=50):
        if self.dataFrame is None:
            return

        self.setupPlots(width, height)

        self.dataFrame.plot(kind='line', 
            title="Moisture and Light Percentage",
            xlabel="Day/Month/Year Hour:Min:Sec",
            ylabel="Percentage %",
            x='timestamp', 
            ylim=(0,100), 
            y=['moist', 'uva'])

        plt.show()

    def addMessageToDataFrame(self, dataMessage: dict, unitsMessage: dict):

        df = pd.DataFrame([{
            **dataMessage
        }])

        if self.dataFrame is None:
            self.dataFrame = df
        else:
            self.dataFrame = pd.concat([self.dataFrame, df], ignore_index=True)

        if self.unitsDict is None:
            self.unitsDict = unitsMessage

    def dataFrameToJson(self):
        if self.dataFrame is None or self.unitsDict is None:
            return json.dumps({"error": "No data available"})

        json_data = {
            "sensor_data": self.dataFrame.to_dict(orient="records"),
            "sensor_units": self.unitsDict
        }

        return json.dumps(json_data, indent=4)


    def uploadOutRecords(self, remoteDir=REMOTE_DIR, un=REMOTE_UN, host=REMOTE_HOST):
        # Ensure the local directory exists
        if not os.path.isdir(self.outRecordsDir):
            print("Local directory, ", self.outRecordsDir, " does not exist.")
            return False

        # Get all files in the directory (ignoring subdirectories)
        files = [f for f in os.listdir(self.outRecordsDir) if os.path.isfile(os.path.join(self.outRecordsDir, f))]
        
        if not files:
            print("No files to upload in ./outRecords/")
            return False

        # Construct SCP command to copy files directly into remote_path
        scp_command = ["scp"] + [os.path.join(self.outRecordsDir, f) for f in files] + [f"{un}@{host}:{remoteDir}"]

        try:
            result = subprocess.run(scp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                print("Files successfully uploaded to RangerLab.")
                # Delete local files after successful upload
                for f in files:
                    os.remove(os.path.join(self.outRecordsDir, f))
                print("Deleted local files after upload.")
                return True
            else:
                print(f"SCP upload failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    def isRangerLabReachable(self, host="192.168.0.100", username="ranger", port=22, timeout=5):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Auto-accept unknown keys

        try:
            ssh.connect(
                hostname=host,
                port=port,
                username=username,
                timeout=timeout,
            )
            ssh.close()
            return True  # Connection successful
        except Exception as e:
            print(f"SSH Connection Failed: {e}")
            return False  # Connection failed


class LiveRecord(Record):
    
    def __init__(self, lifespan: float):
        super().__init__()
        
        self._timer = threading.Timer(lifespan, self._self_destruct)
        self._timer.daemon = True
        self._timer.start()

        self.isLive = True

    def _self_destruct(self):
        self.isLive = False
        self.saveJsonToFile()
        if self.isRangerLabReachable():
            self.uploadOutRecords()

    def saveJsonToFile(self):
        if self.dataFrame is None or self.dataFrame.empty:
            print("No data available to save.")
            return

        # Get the timestamp of the first entry
        first_timestamp = self.dataFrame.iloc[0].get("timestamp", None)
        if first_timestamp is None:
            print("No valid timestamp in the data.")
            return

        # Format timestamp as YYYYmmddHHMMSS
        formatted_time = toDateStr(first_timestamp)

        # Create output directory if it doesn't exist
        os.makedirs(self.outRecordsDir, exist_ok=True)

        # Define file path
        file_path = os.path.join(self.outRecordsDir, f"record.{formatted_time}.json")

        # Get JSON data
        json_data = self.dataFrameToJson()

        # Write JSON to file
        with open(file_path, "w") as json_file:
            json_file.write(json_data)

        print(f"Record saved to {file_path}")

    def processMessage(self, message: dict):
        dataMessage = message["sensor_data"]
        dataMessage["timestamp"] = time.time()
        unitsMessage = message["sensor_units"]
        self.addMessageToDataFrame(dataMessage, unitsMessage)

    def addMessageToDataFrame(self, dataMessage: dict, unitsMessage: dict):
        # Call the superclass method to reuse existing logic
        super().addMessageToDataFrame(dataMessage, unitsMessage)

        # Store only the latest entry if data exists
        if self.dataFrame is not None and not self.dataFrame.empty:
            self.latestDataFrame = self.dataFrame.iloc[[-1]]  # Keep only the last row

    def latestDataFrameToText(self) -> str:
        if self.latestDataFrame is None or self.latestDataFrame.empty:
            return "No data available"

        latest_entry = self.latestDataFrame.iloc[-1].to_dict()  # Get the last row as a Series
        timestampDate = time.asctime(time.localtime(latest_entry.get("timestamp", "???")))
        timestamp = timestampDate
        formatted_text = f"{timestamp}\n"

        for sensor, value in latest_entry.items():
            if sensor == "timestamp":
                continue  # Skip timestamp since it's already added
            unit = self.unitsDict.get(sensor, "")  # Get unit from unitsDict
            formatted_text += f"   {sensor}: {value} {unit}\n"

        return formatted_text.strip()  # Remove trailing newline 

class ArchiveRecord(Record):
    def __init__(self, start, end, timeFmt="%m/%d/%Y %H:%M:%S"):
        super().__init__()
        self.start = start
        self.end = end
        self.fetchArchive()
        self.archiveFilesToDataFrame()
        
        local_tz = "America/New_York"

        if self.dataFrame is not None:
            self.dataFrame['timestamp'] = (
                pd.to_datetime(self.dataFrame['timestamp'], unit='s')
                .dt.tz_localize('UTC')
                .dt.tz_convert(local_tz)
                .dt.strftime(timeFmt)
            )

    def matchRemoteRecords(self, un=REMOTE_UN, host=REMOTE_HOST):
        # SSH command to filter files by timestamp range using grep
        ssh_command = (
            f'ssh {un}@{host} "ls {REMOTE_DIR}/record.*.json | '
            f'grep -E \'record\\.([0-9]{{14}})\\.json\' | '
            f'awk -F. \'\\$2 >= {self.start} && \\$2 <= {self.end}\' "'
        )

        try:
            # Run SSH command
            result = subprocess.run(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                print(f"Failed to list remote files: {result.stderr}")
                return []

            # Process output and return matching file paths
            remote_files = result.stdout.strip().split("\n")
            return [f"{file}" for file in remote_files if file]

        except Exception as e:
            print(f"Error: {e}")
            return []

    def fetchArchive(self, un=REMOTE_UN, host=REMOTE_HOST):

        # Get the list of matching files
        matching_files = self.matchRemoteRecords()

        if not matching_files:
            print("No matching files found for the given time range.")
            return

        # Ensure local directory exists
        os.makedirs(self.inRecordsDir, exist_ok=True)

        self.clearInRecords()

        # Iterate through the list and copy each file using SCP
        for file in matching_files:
            remote_path = f"{file}"

            scp_command = f"scp {un}@{host}:{remote_path} {self.inRecordsDir}"
            try:
                subprocess.run(scp_command, shell=True, check=True)
                print(f"Copied {file} to {self.inRecordsDir}")
            except subprocess.CalledProcessError as e:
                print(f"Error copying {file}: {e}")

    def clearInRecords(self):
        """
        Deletes all files in self.inRecords.
        """
        if not os.path.exists(self.inRecordsDir):
            print(f"Directory {self.inRecordsDir} does not exist.")
            return

        # Loop through all files in the directory and delete them
        for file in os.listdir(self.inRecordsDir):
            file_path = os.path.join(self.inRecordsDir, file)
            
            # Ensure it's a file before attempting to delete
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

    def archiveFilesToDataFrame(self):
        all_data = []
        units_dict = None  # Store units from the first file

        # Ensure the directory exists
        if not os.path.exists(self.inRecordsDir):
            print(f"Directory {self.inRecordsDir} does not exist.")
            return None

        # Loop through all JSON files in the directory
        for file in sorted(os.listdir(self.inRecordsDir)):  # Sorted to maintain chronological order
            file_path = os.path.join(self.inRecordsDir, file)

            if file.startswith("record.") and file.endswith(".json") and os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)

                    # Extract sensor data and append to list
                    all_data.extend(data["sensor_data"])

                    # Capture units from the first file
                    if units_dict is None:
                        units_dict = data.get("sensor_units", {})

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

        # Convert the list of sensor data to a DataFrame
        df = pd.DataFrame(all_data) if all_data else None

        self.dataFrame = df
        self.unitsDict = units_dict
