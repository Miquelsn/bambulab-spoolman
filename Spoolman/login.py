import requests
from helper_logs import logger
from tools import ReadCredentials, SaveNewToken


def _valid_port(value):
    try:
        port = int(value)
    except (TypeError, ValueError):
        return False
    return 1 <= port <= 65535


# Test the Spoolman API endpoint
def TestSpoolmanApi(ip, port):
    if not ip or not _valid_port(port):
        logger.log_error("Spoolman host or port is invalid.")
        return False
    url = f"http://{ip}:{port}/api/v1/info"
    try:
        response = requests.get(url, timeout=5)  # Timeout after 5 seconds
        if response.status_code == 200:
            logger.log_info("Spoolman API is working correctly!")
            return True
        else:
            logger.log_error(
                f"Spoolman health check failed (HTTP {response.status_code})."
            )
    except requests.RequestException as error:
        logger.log_warning(
            f"Spoolman is unavailable at {ip}:{port}: {error}",
            event="spoolman_unavailable",
            subsystem="spoolman",
        )
    return False


def SaveSpoolmanSettings(ip, port):
    """Validate and save Spoolman settings submitted by the GUI."""
    ip = str(ip or "").strip()
    port = str(port or "7912").strip()
    if not ip or not _valid_port(port):
        return {
            "status": "invalid",
            "message": "Enter a host and a port between 1 and 65535.",
        }
    if not TestSpoolmanApi(ip, port):
        return {
            "status": "unavailable",
            "message": "Spoolman could not be reached with these settings.",
        }
    SaveNewToken("spoolman_ip", ip)
    SaveNewToken("spoolman_port", port)
    logger.log_info(f"Spoolman configuration completed: IP={ip}, Port={port}")
    return {"status": "success", "message": "Connected to Spoolman."}


def ConfigureSpoolmanApi():
    """Check saved settings without ever prompting in the terminal."""
    credentials = ReadCredentials()
    spoolman_ip = credentials.get("DEFAULT", "spoolman_ip", fallback=None)
    spoolman_port = credentials.get("DEFAULT", "spoolman_port", fallback=None)
    if spoolman_ip and spoolman_port:
        if TestSpoolmanApi(spoolman_ip, spoolman_port):
            logger.log_info("Spoolman configuration working")
            return True
    logger.log_warning("Configure Spoolman from the Settings page in the GUI.")
    return False
