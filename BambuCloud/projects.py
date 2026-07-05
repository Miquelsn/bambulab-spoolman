import requests
from helper_logs import logger
from tools import ReadCredentials


BASE_URL = "https://api.bambulab.com/v1"
REQUEST_TIMEOUT = 30


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


def GetJobID(taskID):
    if taskID is None or str(taskID).strip() in ("", "0"):
        logger.log_error("Error with task ID")
        return
    # Load credentials from the file
    credentials = ReadCredentials()
    access_token = credentials.get("DEFAULT", "access_token", fallback=None)
    if not access_token:
        logger.log_error("Cannot load task details without a Bambu Cloud token.")
        return None
    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {access_token}"
    try:
        # Concatenate the base URL with the task ID
        url = BASE_URL + "/iot-service/api/user/task/" + str(taskID)
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            json_data = response.json()
            if "job_id" in json_data:
                return json_data["job_id"]
            else:
                logger.log_error("Bambu Cloud did not return a job ID for the task.")
        else:
            logger.log_error(
                f"Failed to get the Bambu Cloud job ID (HTTP {response.status_code})."
            )
    except (requests.RequestException, ValueError) as error:
        logger.log_exception(error)
    return None


def GetTaskDetail(jobID):
    if jobID is None or str(jobID).strip() in ("", "0"):
        logger.log_error("Error with task ID")
        return
    # Load credentials from the file
    credentials = ReadCredentials()
    access_token = credentials.get("DEFAULT", "access_token", fallback=None)
    if not access_token:
        logger.log_error("Cannot load task details without a Bambu Cloud token.")
        return None
    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {access_token}"

    try:
        url = BASE_URL + "/user-service/my/tasks"
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            json_data = response.json()
            hits = json_data.get("hits", [])
            if hits:
                for hit in hits:
                    if "id" in hit:
                        if str(hit["id"]) == str(jobID):
                            return hit
            else:
                logger.log_error("No hits available.")
        else:
            logger.log_error(
                f"Failed to get Bambu Cloud tasks (HTTP {response.status_code})."
            )
        return None
    except (requests.RequestException, ValueError) as error:
        logger.log_exception(error)
        return None


def GetTaksDetail(jobID):
    """Backward-compatible alias for the original misspelled function."""
    return GetTaskDetail(jobID)
