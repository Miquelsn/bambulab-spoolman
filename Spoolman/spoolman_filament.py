import requests
import os
from tools import *

class SpoolmanFilament:
    def __init__(self):
        self.spoolId = None
        self.filamentId = None
        self.filament_name = None
        self.filament_vendor_name = None
        self.filament_type = None
    
    def __str__(self):
        return f"Filament Name: {self.filament_name}, Filament Type: {self.filament_type}, Filament Vendor: {self.filament_vendor_name}, Spool ID: {self.spoolId}, Filament ID: {self.filamentId}"



def GetSpoolmanFilaments():
    # Load credentials from the file
    credentials = ReadCredentials()
    spoolman_ip = credentials.get("spoolman_ip")
    spoolman_port = credentials.get("spoolman_port")
    url = f"http://{spoolman_ip}:{spoolman_port}/api/v1/spool"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get spoolman filaments with status code {response.status_code}: {response.text}")  
    except Exception as e:
        print(f"An error occurred while getting the spoolman filaments: {e}")    
    return None

def ProcessSpoolmanFilament(filaments):
    filaments_list = []
    unique_ids = set()  # To track unique filament IDs
    for filament in filaments:

        spoolman_filament = SpoolmanFilament()
        
        spoolman_filament.spoolId = filament["id"]
        spoolman_filament.filamentId = filament["filament"]["id"]
        spoolman_filament.filament_name = filament["filament"]["name"]
        spoolman_filament.filament_vendor_name = filament["filament"]["vendor"]["name"]
        
        spoolman_filament.filament_type = filament["filament"]["material"]
        # Ensure is unique by filamentID
        if spoolman_filament.spoolId not in unique_ids:
            filaments_list.append(spoolman_filament)
            unique_ids.add(spoolman_filament.spoolId)  # Add ID to the set
        else:
            print(f"Filament with ID {spoolman_filament.spoolId} already exists")
            
    for filament in filaments_list:
        print(filament)
    print("Final count: ", len(filaments_list))
    
filaments = GetSpoolmanFilaments()
if filaments:
    ProcessSpoolmanFilament(filaments)
else:
    print("Error no filaments")