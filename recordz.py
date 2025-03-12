import time
import threading
import pandas as pd
import json
import os

class Record:
 
    dataFrame = None
    latestDataFrame = None
    unitsDict = None

    def __init__(self):
        self.dataFrame = None

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

    def toDateStr(self, timeStmp):
        return time.strftime("%m/%d/%Y", time.localtime(timeStmp))

    def toTimeStr(self, timeStmp):
        return time.strftime("%H:%M:%S", time.localtime(timeStmp))


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
        formatted_time = time.strftime("%Y%m%d%H%M%S", time.localtime(first_timestamp))

        # Create output directory if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "outRecords")
        os.makedirs(output_dir, exist_ok=True)

        # Define file path
        file_path = os.path.join(output_dir, f"record.{formatted_time}.json")

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
        timestampDate = self.toDateStr(latest_entry.get("timestamp", "???"))
        timestampTime = self.toTimeStr(latest_entry.get("timestamp", "???"))
        timestamp = timestampDate + " " + timestampTime
        formatted_text = f"Time Stamp: {timestamp}\n"

        for sensor, value in latest_entry.items():
            if sensor == "timestamp":
                continue  # Skip timestamp since it's already added
            unit = self.unitsDict.get(sensor, "")  # Get unit from unitsDict
            formatted_text += f"   {sensor}: {value} {unit}\n"

        return formatted_text.strip()  # Remove trailing newline 


test_message1 = {"sensor_data": {"uva": 1.2, "uvb": 3.3}, "sensor_units": {"uva": "%", "uvb": "%"}}
test_message2 = {"sensor_data": {"uva": 5.7, "uvb": 8.0}, "sensor_units": {"uva": "%", "uvb": "%"}}

testLR = LiveRecord(2)
testLR.processMessage(test_message1)
testLR.processMessage(test_message2)
time.sleep(5)
