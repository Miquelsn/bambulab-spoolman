import os
import sys
import time

import BambuCloud.login
from BambuPrinter.bambu_printer import *
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import BambuCloud as BambuCloud
import Local_MQTT.local_mqtt as MQTT
import Spoolman.login  as Spoolman
import BambuPrinter as BambuPrinter

# Get Bambu Cloud Credentails
if BambuCloud.login.TestToken() == False:
  BambuCloud.login_and_get_token()
  if BambuCloud.login.TestToken() == False:
    print("Failed to get token. Retrying in 5 minutes.")
    time.sleep(300)
    exit()


# Get the IP of the printer
MQTT.GetPrinterIP()

# Get the IP of Spoolman
Spoolman.ConfigureSpoolmanApi()


# Start and connect to the local MQTT broker
MQTT.StartMQTT()
print("FSM Started. Type 'exit' to exit.")
while 1:
  time.sleep(1)
  #Exit if user type exit
  if input() == "exit":
    exit()
  pass


