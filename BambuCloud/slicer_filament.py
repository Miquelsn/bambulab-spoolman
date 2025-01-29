import requests
import os
from tools import *
import json


slicer_version = "1.10.0.89"
URL = f"https://api.bambulab.com/v1/iot-service/api/slicer/setting?version={slicer_version}"


HEADERS = {
    "User-Agent": "bambu_network_agent/01.09.05.01",
    "X-BBL-Client-Name": "OrcaSlicer",
    "X-BBL-Client-Type": "slicer",
    "X-BBL-Client-Version": "01.09.05.51",
    "X-BBL-Language": "en-US",
    "X-BBL-OS-Type": "linux",
    "X-BBL-OS-Version": "6.2.0",
    "X-BBL-Agent-Version": "01.09.05.01",
    "X-BBL-Executable-info": "{}",
    "X-BBL-Agent-OS-Type": "linux",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

class SlicerFilament:
    def __init__(self):
        self.filamentID = None
        self.filament_name = None
        self.filament_vendor = None
        self.filament_type = None
    
    def __str__(self):
        return f"Filament Name: {self.filament_name}, Filament Type: {self.filament_type}, Filament Vendor: {self.filament_vendor}, Filament ID: {self.filamentID}"

def GetSlicerFilaments():
    # Load credentials from the file
    credentials = ReadCredentials()
    ACCES_TOKEN = credentials.get('access_token')
    HEADERS['Authorization'] = f"Bearer {ACCES_TOKEN}"
    try:
        response = requests.get(URL, headers=HEADERS)
        if response.status_code == 200:
            private_filament = response.json()
            private_filament = private_filament["filament"]["private"]
            return private_filament
        else:
            print(f"Failed to get tasks with status code {response.status_code}: {response.text}")  
    except Exception as e:
        print(f"An error occurred while getting the tasks: {e}")    
    return None

def ProcessSlicerFilament(filaments):
    filaments_list = []
    unique_ids = set()  # To track unique filament IDs
    for filament in filaments:
        slicer_filament = SlicerFilament()
        slicer_filament.filamentID = filament["filament_id"]
         # Extract the part of the name before '@'
        slicer_filament.filament_name = filament["name"].split('@')[0].strip()
        slicer_filament.filament_vendor = filament["filament_vendor"]
        slicer_filament.filament_type = filament["filament_type"]
        # Ensure is unique by filamentID
        if slicer_filament.filamentID not in unique_ids:
            filaments_list.append(slicer_filament)
            unique_ids.add(slicer_filament.filamentID)  # Add ID to the set
    return filaments_list

    
def SaveFilamentsToFile(filaments):
    filename = "slicer_filaments.txt"
    try:
        with open(filename, "w", encoding="utf-8") as file:
            for filament in filaments:
                file.write(str(filament) + "\n")
        print(f"Bambu Studio filaments saved successfully to {filename}")
    except Exception as e:
        print(f"An error occurred while saving filaments: {e}")