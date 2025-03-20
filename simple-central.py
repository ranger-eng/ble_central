#PDX-FileCopyrightText: 2020 Mark Raleson
#
# SPDX-License-Identifier: MIT

# Read sensor readings from peripheral BLE device using a JSON characteristic.

from ble_json_service import SensorService
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
import time
from recordz import LiveRecord
from displayz import Displayz

ble = BLERadio()
connection = None

LOG_CADENCE = 60*1.5 # [s]
RECORD_LIFESPAN = 60*10 # [s]
live_record = None

rpi_display = Displayz()

while True:
    if not connection:
        print("Scanning for BLE device advertising our sensor service...")
        for adv in ble.start_scan(ProvideServicesAdvertisement):
            if SensorService in adv.services:
                connection = ble.connect(adv)
                print("Connected")
                break
        ble.stop_scan()

    if connection and not connection.connected:
        if live_record is not None:
            live_record.saveJsonToFile()
            live_record.isLive = False
        print("Scanning for BLE device advertising our sensor service...")
        rpi_display.dispRawText("Connected: False")
        for adv in ble.start_scan(ProvideServicesAdvertisement):
            if SensorService in adv.services:
                connection = ble.connect(adv)
                print("Connected")
                break
        ble.stop_scan()

    if connection and connection.connected:
        service = connection[SensorService]
        while connection and connection.connected:

            while connection.connected and service.sensors is None:
                pass

            if live_record is None:
                live_record = LiveRecord(RECORD_LIFESPAN) 
            
            if live_record.isLive:
                print("Ranger Lab Reachable: " + str(live_record.isRangerLabReachable("192.168.0.100")))
                live_record.processMessage(service.sensors)
                text_to_disp = "Connected: " + str(connection.connected) + "\n" + live_record.latestDataFrameToText()
                print(text_to_disp)
                rpi_display.dispRawText(text_to_disp)
            else:
                live_record = LiveRecord(RECORD_LIFESPAN)

            time.sleep(LOG_CADENCE)
