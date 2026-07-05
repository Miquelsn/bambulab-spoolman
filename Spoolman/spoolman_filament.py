import requests
import json
from helper_logs import logger
from tools import ReadCredentials


REQUEST_TIMEOUT = 15


class SpoolmanFilament:
    def __init__(self):
        self.spoolId = None
        self.filament_name = None
        self.filament_vendor_name = None
        self.filament_type = None

    def __str__(self):
        return f"Filament Name: {self.filament_name}, Filament Type: {self.filament_type}, Filament Vendor: {self.filament_vendor_name}, Filament ID: {self.spoolId}"


def _api_base_url():
    credentials = ReadCredentials()
    spoolman_ip = credentials.get("DEFAULT", "spoolman_ip", fallback=None)
    spoolman_port = credentials.get("DEFAULT", "spoolman_port", fallback=None)
    if not spoolman_ip or not spoolman_port:
        return None
    return f"http://{spoolman_ip}:{spoolman_port}/api/v1"


def _spool_summary(spool):
    if not isinstance(spool, dict):
        return {}
    filament = spool.get("filament")
    filament = filament if isinstance(filament, dict) else {}
    vendor = filament.get("vendor")
    vendor = vendor if isinstance(vendor, dict) else {}
    return {
        "spoolman_spool_id": spool.get("id"),
        "spoolman_spool_name": filament.get("name"),
        "spoolman_filament_type": filament.get("material"),
        "spoolman_vendor": vendor.get("name"),
        "spoolman_remaining_weight": spool.get("remaining_weight"),
    }


def GetSpool(spool_id):
    base_url = _api_base_url()
    if base_url is None:
        return None
    try:
        response = requests.get(f"{base_url}/spool/{spool_id}", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        logger.log_error(
            f"Failed to load Spoolman spool #{spool_id} (HTTP {response.status_code}).",
            event="spoolman_spool_load_failed",
            subsystem="spoolman",
            spool_id=spool_id,
            status_code=response.status_code,
        )
    except (requests.RequestException, ValueError) as error:
        logger.log_exception(
            error,
            event="spoolman_spool_load_failed",
            subsystem="spoolman",
            spool_id=spool_id,
        )
    return None


def _use_spool(spool_id, weight):
    base_url = _api_base_url()
    if base_url is None:
        return None, "Spoolman is not configured."
    try:
        response = requests.put(
            f"{base_url}/spool/{spool_id}/use",
            json={"use_weight": float(weight)},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            return response.json(), None
        return None, f"Spoolman returned HTTP {response.status_code}."
    except (requests.RequestException, ValueError) as error:
        return None, str(error)


def _set_used_weight(spool_id, used_weight):
    base_url = _api_base_url()
    if base_url is None:
        return False, "Spoolman is not configured."
    try:
        response = requests.patch(
            f"{base_url}/spool/{spool_id}",
            json={"used_weight": max(0.0, float(used_weight))},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            return True, None
        return False, f"Spoolman returned HTTP {response.status_code}."
    except requests.RequestException as error:
        return False, str(error)


def GetSpoolmanFilaments():
    # Load credentials from the file
    credentials = ReadCredentials()
    spoolman_ip = credentials.get("DEFAULT", "spoolman_ip", fallback=None)
    spoolman_port = credentials.get("DEFAULT", "spoolman_port", fallback=None)
    if not spoolman_ip or not spoolman_port:
        logger.log_error("Spoolman is not configured.")
        return []
    url = f"http://{spoolman_ip}:{spoolman_port}/api/v1/spool"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        else:
            logger.log_error(
                f"Failed to get Spoolman filaments (HTTP {response.status_code})."
            )
    except (requests.RequestException, ValueError) as error:
        logger.log_exception(error)
    return []


def ProcessSpoolmanFilament(filaments):
    filaments_list = []
    unique_ids = set()  # To track unique filament IDs
    for filament in filaments or []:
        if not isinstance(filament, dict):
            continue
        spoolman_filament = SpoolmanFilament()

        # Ensure safe access to dictionary fields
        spoolman_filament.spoolId = filament.get("id")
        filament_data = filament.get("filament")
        if not isinstance(filament_data, dict):
            filament_data = {}
        spoolman_filament.filament_name = filament_data.get("name")

        vendor_data = filament_data.get("vendor")
        if not isinstance(vendor_data, dict):
            vendor_data = {}
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
    try:
        with open("filament_mapping.json", "r", encoding="utf-8") as file:
            mapping = json.load(file)
            return mapping if isinstance(mapping, dict) else {}
    except (OSError, json.JSONDecodeError) as error:
        logger.log_error(f"Could not load filament_mapping.json: {error}")
        return {}


def GetSpoolmanID(filament_mapping, slicer_filamentID, printer_id=None):
    # A printer-specific override allows two printers using the same slicer
    # profile to consume different physical Spoolman spools. Existing flat
    # mappings remain the default and require no migration.
    if printer_id:
        printer_key = f"{printer_id}::{slicer_filamentID}"
        if printer_key in filament_mapping:
            return filament_mapping[printer_key]
    return filament_mapping.get(slicer_filamentID)


def RegisterFilamentUsage(
    slicer_filamentID,
    weight,
    printer_id=None,
    spool_id=None,
):
    """Report usage and return a structured result suitable for task history."""
    if not slicer_filamentID:
        logger.log_error("Cannot report filament usage without a slicer filament ID.")
        return {"success": False, "error": "Missing slicer filament ID."}
    try:
        weight = float(weight)
    except (TypeError, ValueError):
        logger.log_error(f"Invalid filament usage weight: {weight}")
        return {"success": False, "error": "Invalid filament usage weight."}
    if weight <= 0:
        return {"success": True, "spoolman_spool_id": spool_id}

    if spool_id is None:
        filament_mapping = LoadFilamentMapping()
        spool_id = GetSpoolmanID(
            filament_mapping, slicer_filamentID, printer_id=printer_id
        )

    if spool_id is None:
        printer_text = f" on printer {printer_id}" if printer_id else ""
        logger.log_error(
            f"No corresponding Spoolman spool for {slicer_filamentID}{printer_text}",
            event="spoolman_mapping_missing",
            subsystem="spoolman",
            printer_id=printer_id,
            slicer_filament_id=slicer_filamentID,
        )
        return {"success": False, "error": "No mapped Spoolman spool."}

    spool, error = _use_spool(spool_id, weight)
    if spool is None:
        logger.log_error(
            f"Failed to register {weight:g} g on Spoolman spool #{spool_id}: {error}",
            event="spoolman_usage_failed",
            subsystem="spoolman",
            printer_id=printer_id,
            spool_id=spool_id,
            weight=weight,
        )
        return {
            "success": False,
            "spoolman_spool_id": spool_id,
            "error": error or "Spoolman usage update failed.",
        }

    result = {"success": True, **_spool_summary(spool)}
    logger.log_info(
        f"Reported {weight:g} g to Spoolman spool #{spool_id}.",
        event="spoolman_usage_reported",
        subsystem="spoolman",
        printer_id=printer_id,
        spool_id=spool_id,
        weight=weight,
    )
    return result


def RegisterFilament(slicer_filamentID, weight, printer_id=None):
    """Backward-compatible boolean wrapper around structured reporting."""
    return RegisterFilamentUsage(
        slicer_filamentID,
        weight,
        printer_id=printer_id,
    )["success"]


def ReassignFilamentUsage(old_spool_id, new_spool_id, weight, printer_id=None):
    """Move previously reported usage between spools with compensation on failure."""
    try:
        weight = float(weight)
    except (TypeError, ValueError):
        return {"success": False, "error": "Invalid filament usage weight."}
    if weight <= 0:
        return {"success": False, "error": "Usage weight must be greater than zero."}

    old_spool_id = str(old_spool_id) if old_spool_id is not None else None
    new_spool_id = str(new_spool_id)
    if old_spool_id == new_spool_id:
        spool = GetSpool(new_spool_id)
        return {"success": True, **_spool_summary(spool)}

    original_used_weight = None
    if old_spool_id is not None:
        old_spool = GetSpool(old_spool_id)
        if old_spool is None:
            return {"success": False, "error": "Could not load the current spool."}
        try:
            original_used_weight = float(old_spool.get("used_weight"))
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": "The current spool has no usable weight history.",
            }
        if original_used_weight + 0.001 < weight:
            return {
                "success": False,
                "error": "The current spool does not contain enough recorded usage to move.",
            }
        refunded, error = _set_used_weight(old_spool_id, original_used_weight - weight)
        if not refunded:
            return {
                "success": False,
                "error": f"Could not refund the current spool: {error}",
            }

    new_spool, error = _use_spool(new_spool_id, weight)
    if new_spool is None:
        if old_spool_id is not None and original_used_weight is not None:
            _set_used_weight(old_spool_id, original_used_weight)
        return {
            "success": False,
            "error": f"Could not apply usage to the new spool: {error}",
        }

    logger.log_info(
        f"Moved {weight:g} g from Spoolman spool "
        f"#{old_spool_id or 'unreported'} to #{new_spool_id}.",
        event="spoolman_usage_reassigned",
        subsystem="spoolman",
        printer_id=printer_id,
        old_spool_id=old_spool_id,
        new_spool_id=new_spool_id,
        weight=weight,
    )
    return {"success": True, **_spool_summary(new_spool)}
