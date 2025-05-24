import re
import time
import paho.mqtt.client as mqtt

from helper_logs import logger
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
    printer_ip = credentials.get('DEFAULT','printer_ip', fallback = None)
    
    if printer_ip and IsValidIp(printer_ip):
        logger.log_info(f"printer_ip found in credentials: {printer_ip}")
        if CheckMQTTConnection():
            logger.log_info("Successfully connected to BambuLab Printer.")
            return
        else: 
            logger.log_error("Failed to connect to BambuLab Printer. Ensure printer is power" 
                 " on and connected to the network.")

    printer_ip = input("Enter your printer_ip (e.g., 192.168.1.100): ")
    while True:
        if IsValidIp(printer_ip):
            SaveNewToken("printer_ip", printer_ip)
            if CheckMQTTConnection():
                logger.log_info("Successfully connected to BambuLab Printer.")
                break
        else:
            logger.log_error("Invalid IP address. Ensure printer is power on and connected "
                  "to the network.\nPlease try again.")

def CheckMQTTConnection():
    """Checks if the MQTT broker is reachable at the given IP."""
    credentials = ReadCredentials()
    password = credentials.get('DEFAULT','password', fallback = None)
    printer_ip = credentials.get('DEFAULT','printer_ip', fallback = None)
    client = mqtt.Client()
    client.username_pw_set(USERNAME, password)
    client.tls_set(cert_reqs=ssl.CERT_NONE)  # Disable certificate verification
    client.tls_insecure_set(True)  # Allow insecure TLS connections
    try:
        client.connect(printer_ip, PORT, 60)
        client.disconnect()
        return True
    except Exception as e:
        logger.log_exception(e)
        return False
    
# Callback when connecting to MQTT Broker
def OnConnect(client, userdata, flags, rc):
    credentials = ReadCredentials()
    TOPIC_REPORT = f"device/{credentials.get('DEFAULT','dev_id', fallback= None)}/report"
    # Subscribe to report topic
    client.subscribe(TOPIC_REPORT)
        
# Callback for received messages
def OnMessage(client, userdata, msg):
    try:
        bp.bambu_printer.ProccessMQTTMsg(msg)
    except Exception as e:
        logger.log_exception(e)
    
def SendStatusMessage(client):
    """Sends a message to the local MQTT broker."""
    credentials = ReadCredentials()
    dev_id = credentials.get('DEFAULT','dev_id', fallback= None)
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
    dev_acces_code = credentials.get('DEFAULT','dev_acces_code', fallback= None)
    printer_ip = credentials.get('DEFAULT','printer_ip', fallback= None)
    client = mqtt.Client()
    client.clean_session = True
    client.username_pw_set(USERNAME, dev_acces_code)
    client.tls_set(cert_reqs=ssl.CERT_NONE)  # Disable certificate verification
    client.tls_insecure_set(True)  # Allow insecure TLS connections
    # Set callbacks
    client.on_connect = OnConnect
    client.on_message = OnMessage
    client.connect(printer_ip, PORT, 60)
    client.loop_start()
    logger.log_info(f"Connected to MQTT broker at {printer_ip}")
    time.sleep(5)
    SendStatusMessage(client)
