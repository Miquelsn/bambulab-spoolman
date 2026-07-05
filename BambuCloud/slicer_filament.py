import requests
from helper_logs import logger
from tools import ReadCredentials


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
    access_token = credentials.get("DEFAULT", "access_token", fallback=None)
    if not access_token:
        logger.log_error("Cannot load slicer filaments without a Bambu Cloud token.")
        return []
    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {access_token}"
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        if response.status_code == 200:
            private_filament = response.json()
            if not isinstance(private_filament, dict):
                logger.log_error(
                    "Bambu Cloud returned an unexpected filament response."
                )
                return []
            filament_data = private_filament.get("filament")
            if not isinstance(filament_data, dict):
                return []
            private_profiles = filament_data.get("private")
            return private_profiles if isinstance(private_profiles, list) else []
        else:
            logger.log_error(
                f"Failed to get slicer filaments (HTTP {response.status_code})."
            )
    except (requests.RequestException, ValueError) as error:
        logger.log_exception(error)
    return []


def ProcessSlicerFilament(filaments):
    filaments_list = []
    unique_ids = set()  # To track unique filament IDs
    for filament in filaments or []:
        if not isinstance(filament, dict):
            continue
        filament_id = filament.get("filament_id")
        if not filament_id:
            continue
        slicer_filament = SlicerFilament()
        slicer_filament.filamentID = filament_id
        # Extract the part of the name before '@'
        slicer_filament.filament_name = (
            str(filament.get("name") or "Unknown").split("@")[0].strip()
        )
        slicer_filament.filament_vendor = filament.get("filament_vendor")
        slicer_filament.filament_type = filament.get("filament_type")
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
