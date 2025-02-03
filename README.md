# Bambulab-Spoolman

## Overview
This Python program integrates with Bambu Cloud, the Bambu printer MQTT server, and Spoolman to monitor and report on 3D printing tasks. It retrieves print task information, filament usage, and spool data to generate detailed reports. 

This is currently in the alpha stage. It is functional, but there is still much work to be done to improve ease of use and usability.

## Limitations
- Tested only with a Bambu A1 with AMS Lite. Other printers may work, but this is not guaranteed.
- Designed to work with a single printer.
- Requires access to Bambu Cloud to retrieve model weight and filament usage.
- Filaments must be mapped in the slicer.
- Only works for prints sent from the slicer to the printer. Prints from local SD storage or local connectivity will not provide weight data, as this information is not transmitted locally via MQTT.

## Features
- Retrieves print task details from Bambu Cloud.
- Obtains model weight per filament and filament names from the slicer (Orca Slicer or Bambu Studio).
- Uses the Bambu printer MQTT server to monitor print status in real-time.
- Integrates with Spoolman to fetch filament data and generate usage reports.
- Saves a history of prints.
- Supports multicolor AMS Lite.
- Tracks print progress to report filament usage. If a print is incomplete, it reports the percentage of filament used. (Note: For multicolor prints, accuracy may be affected due to potential layer imbalances and specific color usage variations.)

## Installation & Usage
### Requirements
- Python must be installed.
- Required Python libraries: `paho-mqtt`, `json`, `requests`, `difflib`, and `ref`.

### Setup
1. Run `initialization.py` and follow the terminal instructions:
   - Enter your Bambu Cloud login (email and password).
   - A verification code may be sent to your email for authentication.
   - Input the local IP address of your BambuLab printer.
   - Provide the IP and port of your Spoolman server.
   - Map filaments between the slicer (Bambu Studio or Orca Slicer) and Spoolman spools. This is assisted by an automated matching algorithm based on material, vendor, and name. While it works well in most cases, manual adjustments may be necessary.
2. Once setup is complete, run `main.py`:
   - This script executes all the core logic and should remain running continuously. If using a Raspberry Pi or Linux system, consider setting it up as a service for automatic startup.
   - If new filaments are added, stop the script, rerun `initialization.py`, and restart `main.py`.

## Future Works
- Improved file system, instead of just saving into a .txt to improve security, protection, and performance
- GUI for visualizing tasks, getting metrics, and generating graphics from prints
- Support for multiple printers filtered by ID
- Possible integration with the slicer to avoid the need for Bambu Cloud to report weight and filament
- General improvements over errors


## License
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

## Contributions
Feel free to submit issues and pull requests!

