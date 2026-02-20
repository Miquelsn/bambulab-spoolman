# Bambulab–Spoolman

## Overview

**Bambulab–Spoolman** is a Python backend application with a Flutter frontend that integrates:

- Bambu Lab Cloud  
- The Bambu printer local MQTT server  
- Spoolman  

It monitors 3D printing tasks, retrieves filament usage data, and generates detailed usage reports linked to your spool inventory.

> ⚠ This project is currently in **alpha stage**.  
> It is functional but still under active development, with ongoing improvements in usability and stability.

## Features

- Retrieves print task details from Bambu Cloud
- Obtains model weight per filament and filament names from the slicer (Bambu Studio or Orca Slicer)
- Monitors printer status in real time via MQTT
- Integrates with Spoolman to fetch spool data and generate usage reports
- Saves a history of prints
- Supports multicolor printing with AMS Lite
- Tracks print progress to estimate filament usage  
  - If a print is incomplete, filament usage is scaled according to completion percentage  
  - Note: Multicolor accuracy on incomplete prints may vary due to layer imbalance and uneven color distribution


## Limitations

- Tested only with a Bambu A1 + AMS Lite (other printers may work but are not guaranteed)
- Designed for a single printer setup
- Requires Bambu Cloud access to retrieve model weight and filament usage
- Filaments must be properly mapped in the slicer
- Only works for prints sent from the slicer to the printer  
  - Prints started from SD card or local-only connections will not provide weight data (this data is not transmitted via local MQTT)

# Installation & Usage

## Requirements

- Python 3.x
- Required Python libraries:
  - paho-mqtt
  - requests
  - json
  - difflib
  - re
  - configparser
## Running the Application

The setup process has been simplified.

Simply run:

```bash
python main.py
```
The application will:

Start the backend

Launch the GUI

Open the web interface at: http://{ip}:2323

## Running with Docker

Docker is the recommended approach for headless or always-on deployments.

**Requirements:** [Docker](https://docs.docker.com/get-docker/) with Compose v2.

**1. Create required data files** (only needed once):

On Linux/macOS:
```bash
bash setup.sh
```

On Windows:
```powershell
.\setup.ps1
```

**2. Build and start the container:**

```bash
docker compose up -d
```

**3. Open the web interface:**

Navigate to `http://<host-ip>:2323` in a browser.

**4. Stop the container:**

```bash
docker compose down
```

> Data files (`credentials.ini`, `task.txt`, `filament_mapping.json`, etc.) are stored in the project directory on the host and persist across container restarts and rebuilds.

## First-Time Setup

On first launch:
<img width="1440" height="524" alt="Captura de pantalla 2026-02-15 a las 0 39 06" src="https://github.com/user-attachments/assets/2050eac7-3b73-4f8f-ae51-b38a20c51243" />


Open the Settings tab in the GUI.

Enter:

- Spoolman IP address
- Spoolman port
- Printer local IP address
- Bambu Cloud login (email + password)

<img width="1436" height="696" alt="Captura de pantalla 2026-02-15 a las 0 39 51" src="https://github.com/user-attachments/assets/d4df9d84-c888-44df-ba5c-66befaab412a" />

Save the settings.

Note: If required, a verification code may be sent to your email for Bambu Cloud authentication.
<img width="407" height="678" alt="Captura de pantalla 2026-02-15 a las 0 35 58" src="https://github.com/user-attachments/assets/a0f480df-fe87-4e3f-84e9-7b2a1ae23172" />
<img width="323" height="191" alt="Captura de pantalla 2026-02-15 a las 0 36 05" src="https://github.com/user-attachments/assets/4504fae6-4376-4049-8128-a6ed2eeb166a" />

## Filament Mapping

After completing the settings:

Go to the Filament Map view.

Map slicer filaments (Bambu Studio / Orca Slicer) to Spoolman spools.

<img width="1440" height="580" alt="Captura de pantalla 2026-02-15 a las 0 37 52" src="https://github.com/user-attachments/assets/51f233d1-4f0f-4c6b-8b47-7776f225401e" />
<img width="661" height="467" alt="Captura de pantalla 2026-02-15 a las 0 38 03" src="https://github.com/user-attachments/assets/c3bf0711-19a2-41f0-b904-8136d16b6a95" />

An automated matching algorithm suggests matches based on:

- Material
- Vendor
- Name

Manual adjustments can be made directly in the GUI.

# GUI Overview

The web interface created with Flutter (Port 2323) provides:

- List of recent print tasks
- Real-time terminal output
- Settings management
- Filament mapping interface
- Print history tracking

# Running Continuously

When running via Docker (`docker compose up -d`), the `restart: unless-stopped` policy ensures the application restarts automatically after a reboot or crash.

For bare-metal setups (without Docker), `main.py` must remain running continuously. On Linux or Raspberry Pi it is recommended to configure it as a systemd service for automatic startup.

# Future Work

- Advanced GUI metrics and print analytics
- Graph generation and visualization tools
- Multi-printer support (filtered by ID)
- Possible slicer integration to avoid dependency on Bambu Cloud
- Improved error handling and stability enhancements

# License
GNU General Public License v3.0
29 June 2007

# Contributions
Contributions are welcome.
Feel free to submit issues and pull requests.
