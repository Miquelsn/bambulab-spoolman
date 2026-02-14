import os
import sys
import time
from Gui.WebServer.auto_discover import start_broadcast_thread
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

# Start GUI and websockets connection
logger.log_info("Starting GUI")
flutter_web_server.start_thread()
logger.log_info("GUI started")
logger.log_info("Starting autodiscover")
start_broadcast_thread()
logger.log_info("Autodiscover started")
logger.log_info("Starting WebSockets")
websocket_service.start_websocket_server()
logger.log_info("Websocket started")

# Start and connect to the local MQTT broker
MQTT.StartMQTT()
logger.log_info("FSM Started. Type 'exit' to exit.")

# Main loop (Checks new filaments)
while True:
    try: 
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
        
        # Check every 24 hours (gui can force the check sooner)
        time.sleep(24 * 60 * 60)

    except Exception as e:
        logger.log_exception(e)

