import os
import sys
import time

from helper_logs import logger

from Filament import filament
import BambuCloud.login
import BambuCloud.slicer_filament
from BambuPrinter.bambu_printer import *
import Spoolman.spoolman_filament
import Spoolman.login

import Local_MQTT.local_mqtt as MQTT
import BambuPrinter as BambuPrinter

import Gui.WebServer.flutter_web_server as flutter_web_server

import Gui.WebServer.websockets_service as websocket_service

logger.log_info("Starting GUI")
flutter_web_server.start_thread()
logger.log_info("GUI started")
logger.log_info("Starting WebSockets")
websocket_service.start_websocket_server()
logger.log_info("Websocket started")

# Get Bambu Cloud Credentials
if not BambuCloud.login.TestToken():
    BambuCloud.login.LoginAndGetToken()
    if not BambuCloud.login.TestToken():
        logger.log_error("Failed to get token. Retrying in 5 minutes.")
        time.sleep(300)
        exit()

# Get the IP of the printer
MQTT.GetPrinterIP()

# Get the IP of Spoolman
Spoolman.login.ConfigureSpoolmanApi()

# Save Filaments From Bambu Studio
filaments = BambuCloud.slicer_filament.GetSlicerFilaments()
filaments = BambuCloud.slicer_filament.ProcessSlicerFilament(filaments)
if filaments:
    BambuCloud.slicer_filament.SaveFilamentsToFile(filaments)

# Save Filaments From Spoolman
filaments = Spoolman.spoolman_filament.GetSpoolmanFilaments()
filaments = Spoolman.spoolman_filament.ProcessSpoolmanFilament(filaments)
if filaments:
    Spoolman.spoolman_filament.SaveFilamentsToFile(filaments)

# Map filaments
filament.map_filaments()

# Start and connect to the local MQTT broker
MQTT.StartMQTT()
logger.log_info("FSM Started. Type 'exit' to exit.")


while True:
    try:
        time.sleep(1)
        # Exit if user types 'exit'
        if input() == "exit":
            break
    except Exception as e:
        logger.log_exception(e)

