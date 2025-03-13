#PDX-FileCopyrightText: 2020 Mark Raleson
#
# SPDX-License-Identifier: MIT

# Read sensor readings from peripheral BLE device using a JSON characteristic.

from ble_json_service import SensorService
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
import time
from recordz import LiveRecord

ble = BLERadio()
connection = None

LOG_CADENCE = 1 # [s]
RECORD_LIFESPAN = 10 # [s]
live_record = None

while True:
    if not connection:
        print("Scanning for BLE device advertising our sensor service...")
        for adv in ble.start_scan(ProvideServicesAdvertisement):
            if SensorService in adv.services:
                connection = ble.connect(adv)
                print("Connected")
                break
        ble.stop_scan()

    if connection and connection.connected:
        service = connection[SensorService]
        while connection.connected:
            if live_record is None:
                live_record = LiveRecord(RECORD_LIFESPAN) 
            
            if live_record.isLive:
                live_record.processMessage(service.sensors)
                print(live_record.latestDataFrameToText())
            else:
                live_record = LiveRecord(RECORD_LIFESPAN)

            time.sleep(LOG_CADENCE)
