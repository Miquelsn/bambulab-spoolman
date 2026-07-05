# Bambulab-Spoolman

## Overview
This Python program integrates with Bambu Cloud, the Bambu printer MQTT server, and Spoolman to monitor and report on 3D printing tasks. It retrieves print task information, filament usage, and spool data to generate detailed reports.

This is currently in the alpha stage. It is functional, but there is still much work to be done to improve ease of use and usability.

## Features
- Retrieves print task details from Bambu Cloud.
- Obtains model weight per filament and filament names from the slicer (Orca Slicer or Bambu Studio).
- Uses the Bambu printer MQTT server to monitor print status in real-time.
- Integrates with Spoolman to fetch filament data and generate usage reports.
- Saves a history of prints.
- Serves a responsive web dashboard for printer status, structured activity,
  and editable print history.
- Records the physical Spoolman spool used by each filament and can safely move
  an incorrect historical usage report to another spool.
- Supports multiple printers on the same Bambu account, including independent simultaneous print jobs.
- Supports AMS Lite, standard AMS/external trays, and the newer multi-AMS payload used by H2-series printers.
- Tracks print progress to report filament usage. If a print is incomplete, it reports the percentage of print as the multiplier of the filament used. (Note: For multicolor prints, accuracy may be affected due to potential layer imbalances and specific color usage variations.)

## Limitations
- Multi-printer support is implemented for the existing A1 and H2C workflow, but other printer/firmware combinations have not all been tested.
- Requires access to Bambu Cloud to retrieve model weight and filament usage.
- Filaments must be mapped in the slicer.
- Only works for prints sent from the slicer to the printer. Prints from local SD storage or local connectivity will not provide weight data, as this information is not transmitted locally via MQTT.

## Installation & Usage
### Requirements
- Python 3.9 or newer.
- Flutter is required only when rebuilding the web dashboard.

### Install

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd Gui/bambulab_spoolman
flutter pub get
flutter build web
cd ../..
```

### Setup
1. Run `.venv/bin/python main.py`. The service starts the dashboard first and
   opens `http://127.0.0.1:2323` automatically. It does not request setup values
   in the terminal.
2. Open **Settings** in the dashboard:
   - Connect Bambu Cloud. If email verification is required, enter the code in
     the verification field shown in the GUI. Passwords are used only for the
     current login and are never saved.
   - Select **Discover** to locate bound printers by Bambu LAN announcement.
     When broadcasts are filtered, the service falls back to an authenticated
     scan of the saved local subnet. A manually entered IP remains available as
     a fallback.
   - Add or update each printer's LAN access code. Turn off **Monitor this
     printer** to omit an inactive or unavailable printer; it will not block
     startup or the other printers.
   - Enter the Spoolman host and port, then select **Test and save**.
3. Keep `main.py` running continuously. On Raspberry Pi or Linux, consider
   configuring it as a service. The dashboard's WebSocket API listens on port
   `12346`, and native clients can discover it over UDP port `54545`.

Use **Filaments** in the dashboard to review unmapped slicer profiles, choose a
suggested or searched Spoolman spool, change an existing mapping, or unlink it.

In print history, each filament shows the physical Spoolman spool that received
its usage. Choose **Change** to refund that usage from the old spool and apply it
to the correct one.

Run commands from the repository root because runtime data files are stored there. Stop the service with `Ctrl+C`; MQTT clients are disconnected cleanly.

The old single-printer `credentials.ini` format is migrated automatically. Each
discovered printer receives its own `[printer:<serial>]` section containing its
IP, access code, name, model, and enabled flag. Use **Monitor this printer** in
Settings to change the enabled flag.

By default, both printers use the existing slicer-filament-to-Spoolman mapping. If the same slicer profile represents different physical spools in the two printers, add a printer-specific key to `filament_mapping.json` using `<printer serial>::<filament ID>`. For example:

```json
{
  "GFA00": 10,
  "H2C-SERIAL::GFA00": 20
}
```

In this example, spool 10 is the default and the H2C consumes spool 20 for the same `GFA00` slicer profile.

## Architecture

The service has four main boundaries:

1. Bambu Cloud supplies account-bound printers, project metadata, and slicer filament profiles.
2. One local TLS MQTT connection per printer maintains independent print state and AMS/external-tray inventory.
3. Completed or failed tasks are stored in `data/bambulab_spoolman.sqlite3`, and
   confirmed filament use is sent to Spoolman. Existing `task.txt` history is
   imported automatically once.
4. The Python HTTP and WebSocket services expose the compiled Flutter dashboard,
   structured JSON activity events, live printer state, the Spoolman catalog,
   and enriched print history.

Runtime configuration and renewable access tokens are stored in `credentials.ini` with owner-only permissions on POSIX systems. The Bambu account password is never persisted and any legacy saved password is removed after successful authentication. Task history is stored in an owner-only SQLite database; filament mappings and cached catalogs remain in the gitignored root data files. These controls are not a substitute for an operating-system secret store, so restrict access to the service account and its backups.

The HTTP and WebSocket servers listen on the LAN to support other devices. They do not implement user authentication. Local printer MQTT uses TLS but cannot verify the printer's self-signed certificate. Run this application only on a trusted network, do not forward ports `2323` or `12346` to the internet, and use host firewall rules when the dashboard should be local-only.

## Development Checks

From the repository root:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m compileall -q . -x '(^|/)(\.git|build|\.dart_tool)(/|$)'
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check . --exclude Gui/bambulab_spoolman/build
cd Gui/bambulab_spoolman
flutter analyze
flutter test
flutter build web
```

The development requirements are not needed at runtime.

## Future Works
- Improved file system, instead of just saving into a .txt to improve security, protection, and performance
- Possible integration with the slicer to avoid the need for Bambu Cloud to report weight and filament
- Authenticated or reverse-proxied dashboard access for untrusted networks


## License
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

## Contributions
Feel free to submit issues and pull requests!
