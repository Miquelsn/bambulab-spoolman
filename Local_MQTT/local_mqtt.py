import os
import re

import paho.mqtt.client as mqtt
import ssl
PORT = 8883  # MQTT over TLS
USERNAME = "bblp"  # Fixed username for local MQTT
import json
import BambuPrinter.bambu_printer as bp
from tools import *



def IsValidIp(ip):
    """Validates the format of the given IP address."""
    pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    if pattern.match(ip):
        return all(0 <= int(part) <= 255 for part in ip.split('.'))
    return False

def GetPrinterIP():
    """Checks for printer_ip in credentials or prompts the user to provide one."""
    credentials = ReadCredentials()
    printer_ip = credentials.get('printer_ip')
    
    if printer_ip and IsValidIp(printer_ip):
        print(f"printer_ip found in credentials: {printer_ip}")
        if CheckMQTTConnection():
            print("Successfully connected to BambuLab Printer.")
            return
        else: 
            print("Failed to connect to BambuLab Printer. Ensure printer is power" 
                 " on and connected to the network.")

    printer_ip = input("Enter your printer_ip (e.g., 192.168.1.100): ")
    while True:
        if IsValidIp(printer_ip):
            SaveNewToken("printer_ip", printer_ip)
            if CheckMQTTConnection():
                print("Successfully connected to BambuLab Printer.")
                break
        else:
            print("Invalid IP address. Ensure printer is power on and connected "
                  "to the network.\nPlease try again.")

def CheckMQTTConnection():
    """Checks if the MQTT broker is reachable at the given IP."""
    credentials = ReadCredentials()
    password = credentials.get('password')
    printer_ip = credentials.get('printer_ip')
    client = mqtt.Client()
    client.username_pw_set(USERNAME, password)
    client.tls_set(cert_reqs=ssl.CERT_NONE)  # Disable certificate verification
    client.tls_insecure_set(True)  # Allow insecure TLS connections
    try:
        client.connect(printer_ip, PORT, 60)
        client.disconnect()
        return True
    except Exception as e:
        print(f"Failed to connect to MQTT broker at {printer_ip}: {e}")
        return False
    
# Callback when connecting to MQTT Broker
def OnConnect(client, userdata, flags, rc):
    credentials = ReadCredentials()
    TOPIC_REPORT = f"device/{credentials.get('dev_id')}/report"
    
    # Subscribe to report topic
    client.subscribe(TOPIC_REPORT)
        
# Callback for received messages
def OnMessage(client, userdata, msg):
    bp.bambu_printer.ProccessMQTTMsg(msg)
    
def SendStatusMessage(client):
    """Sends a message to the local MQTT broker."""
    credentials = ReadCredentials()
    dev_id = credentials.get('dev_id')
    topic = f"device/{dev_id}/request"
    message ={
    "pushing": {
        "sequence_id": "0",
        "command": "pushall",
        "version": 1,
        "push_target": 1
    }
    }
    client.publish(topic, json.dumps(message))


def StartMQTT():
    """Starts the local MQTT client and connects to the broker."""
    credentials = ReadCredentials()
    dev_acces_code = credentials.get('dev_access_code')
    printer_ip = credentials.get('printer_ip')
    client = mqtt.Client()
    client.username_pw_set(USERNAME, dev_acces_code)
    client.tls_set(cert_reqs=ssl.CERT_NONE)  # Disable certificate verification
    client.tls_insecure_set(True)  # Allow insecure TLS connections
    # Set callbacks
    client.on_connect = OnConnect
    client.on_message = OnMessage
    client.connect(printer_ip, PORT, 60)
    client.loop_start()
    print(f"Connected to MQTT broker at {printer_ip}")
    SendStatusMessage(client)
