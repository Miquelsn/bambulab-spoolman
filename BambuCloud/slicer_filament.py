import requests
import os
from tools import *
import json
from helper_logs import logger


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
    credentials = ReadCredentials()
    access_token = credentials.get('DEFAULT', 'access_token', fallback=None)

    # 🚫 No token yet → skip quietly
    if not access_token:
        logger.log_info("No BambuCloud access token yet. Skipping slicer filament sync.")
        return []

    headers = HEADERS.copy()
    headers['Authorization'] = f"Bearer {access_token}"

    try:
        response = requests.get(URL, headers=headers, timeout=8)

        # ✅ Success
        if response.status_code == 200:
            data = response.json()

            # Defensive JSON parsing
            filament_section = data.get("filament", {})
            private_filaments = filament_section.get("private", [])

            if not isinstance(private_filaments, list):
                logger.log_error("Unexpected filament format from BambuCloud.")
                return []

            return private_filaments

        # 🔑 Token expired or invalid
        if response.status_code == 401:
            logger.log_error("BambuCloud token expired or invalid.")
            SaveNewToken("access_token", "")  # Clear bad token
            return []

        # 🌐 Other API error
        logger.log_error(
            f"BambuCloud API error {response.status_code}: {response.text[:200]}"
        )

    except requests.exceptions.ConnectTimeout:
        logger.log_error("BambuCloud request timed out.")
    except requests.exceptions.ConnectionError:
        logger.log_error("No internet connection to BambuCloud.")
    except requests.exceptions.RequestException as e:
        logger.log_exception(e)
    except ValueError:
        logger.log_error("Invalid JSON received from BambuCloud.")

    return []

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
        logger.log_info(f"Bambu Studio filaments saved successfully to {filename}")
    except Exception as e:
        logger.log_exception(e)