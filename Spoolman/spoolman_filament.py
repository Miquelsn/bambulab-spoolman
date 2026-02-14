import requests
import os
from tools import *
import json
from helper_logs import logger

class SpoolmanFilament:
    def __init__(self):
        self.spoolId = None
        self.filament_name = None
        self.filament_vendor_name = None
        self.filament_type = None
    
    def __str__(self):
        return f"Filament Name: {self.filament_name}, Filament Type: {self.filament_type}, Filament Vendor: {self.filament_vendor_name}, Filament ID: {self.spoolId}"

def GetSpoolmanFilaments():
    # Load credentials from the file
    credentials = ReadCredentials()
    spoolman_ip = credentials.get('DEFAULT',"spoolman_ip", fallback = None)
    spoolman_port = credentials.get('DEFAULT',"spoolman_port", fallback = None)
    
    # Config missing → silently skip
    if not spoolman_ip or not spoolman_port:
        logger.log_info("Spoolman IP/Port not configured yet. Skipping request.")
        return []

    # Invalid values → skip
    if not IsValidIp(spoolman_ip):
        logger.log_error(f"Invalid Spoolman IP: {spoolman_ip}")
        return []

    if not IsValidPort(spoolman_port):
        logger.log_error(f"Invalid Spoolman Port: {spoolman_port}")
        return []
    
    url = f"http://{spoolman_ip}:{spoolman_port}/api/v1/spool"
    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            return response.json()

        logger.log_error(
            f"Spoolman error {response.status_code}: {response.text[:200]}"
        )

    except requests.exceptions.ConnectTimeout:
        logger.log_error("Spoolman connection timed out.")
    except requests.exceptions.ConnectionError:
        logger.log_error("Could not connect to Spoolman server.")
    except requests.exceptions.RequestException as e:
        logger.log_exception(e)

    return []

def ProcessSpoolmanFilament(filaments):
    filaments_list = []
    unique_ids = set()  # To track unique filament IDs
    for filament in filaments:
        spoolman_filament = SpoolmanFilament()
        
        # Ensure safe access to dictionary fields
        spoolman_filament.spoolId = filament.get("id")
        filament_data = filament.get("filament", {})  # Ensure it's a dict
        spoolman_filament.filament_name = filament_data.get("name")
        
        vendor_data = filament_data.get("vendor", {})  # Ensure vendor is a dict
        spoolman_filament.filament_vendor_name = vendor_data.get("name")

        spoolman_filament.filament_type = filament_data.get("material")

        # Ensure is unique by filamentID
        if spoolman_filament.spoolId not in unique_ids:
            filaments_list.append(spoolman_filament)
            unique_ids.add(spoolman_filament.spoolId)  # Add ID to the set
    return filaments_list

def SaveFilamentsToFile(filaments):
    filename = "spoolman_filaments.txt"
    try:
        with open(filename, "w", encoding="utf-8") as file:
            for filament in filaments:
                file.write(str(filament) + "\n")
        logger.log_info(f"Filaments saved successfully to {filename}")
    except Exception as e:
        logger.log_exception(e)
        
def LoadFilamentMapping():
    with open("filament_mapping.json", "r") as file:
        return json.load(file)    
      
def GetSpoolmanID(filament_mapping, slicer_filamentID):
    return filament_mapping.get(slicer_filamentID)     
  
def RegisterFilament(slicer_filamentID, weight):
    filament_mapping = LoadFilamentMapping()
    spoolman_filamentID = GetSpoolmanID(filament_mapping, slicer_filamentID)
    
    if spoolman_filamentID is None:
        logger.log_error(f"No corresponding spoolman filament for {slicer_filamentID}")
        return False
      
    # Load credentials from the file
    credentials = ReadCredentials()
    spoolman_ip = credentials.get('DEFAULT',"spoolman_ip", fallback = None)
    spoolman_port = credentials.get('DEFAULT',"spoolman_port", fallback = None)
    url = f"http://{spoolman_ip}:{spoolman_port}/api/v1/spool/{spoolman_filamentID}/use"
    payload = {"use_weight": weight}

    try:
        response = requests.put(url, json=payload)
        if response.status_code == 200:
            return True
        else:
            logger.log_error(f"Failed to get spoolman filaments with status code {response.status_code}: {response.text}")  
    except Exception as e:
        logger.log_exception(e)    
    return False