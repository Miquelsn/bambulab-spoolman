import requests
import os
from tools import *
from helper_logs import logger

# API endpoint for login and sending the verification code
LOGIN_URL = "https://api.bambulab.com/v1/user-service/user/login"
SEND_CODE_URL = "https://api.bambulab.com/v1/user-service/user/sendemail/code"
TEST_URL = "https://api.bambulab.com/v1/iot-service/api/user/bind"

LOGIN_SUCCESS = "success"
LOGIN_BAD_CREDENTIALS = "bad_credentials"
LOGIN_NEEDS_CODE = "needs_verification_code"
LOGIN_NETWORK_ERROR = "network_error"
LOGIN_UNKNOWN_ERROR = "unknown_error"

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


def SendVerificationCode():
    # Load credentials from the file
    credentials = ReadCredentials()
    EMAIL = credentials.get('DEFAULT','email', fallback= None)
    PASSWORD = credentials.get('DEFAULT','password', fallback= None)

    # Ensure that the credentials are loaded correctly
    if not EMAIL or not PASSWORD:
        logger.log_error("Missing email or password in credentials file.")
        exit()
        
    """Send a verification code to the user's email."""
    payload = {
        "email": EMAIL,
        "type": "codeLogin"
    }

    try:
        response = requests.post(SEND_CODE_URL, headers=HEADERS, json=payload)
        if response.status_code == 200:
            logger.log_info("Verification code sent to your email.")
            return True
        else:
            logger.log_error(f"Failed to send verification code with status code {response.status_code}: {response.text}")
    except Exception as e:
        logger.log_exception(e)
    return False

def LoginAndGetToken(verification_code=None):
    credentials = ReadCredentials()
    EMAIL = credentials.get('DEFAULT', 'email', fallback=None)
    PASSWORD = credentials.get('DEFAULT', 'password', fallback=None)

    if not EMAIL or not PASSWORD:
        logger.log_error("Missing email or password.")
        return LOGIN_BAD_CREDENTIALS

    payload = {
        "account": EMAIL,
        "password": PASSWORD
    }

    # If we already have a verification code, use it instead
    if verification_code:
        payload = {
            "account": EMAIL,
            "code": verification_code
        }

    try:
        response = requests.post(LOGIN_URL, headers=HEADERS, json=payload, timeout=15)
    except requests.exceptions.RequestException as e:
        logger.log_exception(e)
        return LOGIN_NETWORK_ERROR

    if response.status_code != 200:
        logger.log_error(f"Login failed: {response.status_code} {response.text}")
        return LOGIN_BAD_CREDENTIALS

    data = response.json()
    access_token = data.get("accessToken")

    if access_token:
        SaveNewToken("access_token", access_token)
        logger.log_info("Login successful")
        return LOGIN_SUCCESS

    # 🔐 Verification required
    if data.get("loginType") == "verifyCode":
        logger.log_info("Verification code required")
        if SendVerificationCode():
            return LOGIN_NEEDS_CODE
        else:
            return LOGIN_NETWORK_ERROR

    logger.log_error("Unknown login response")
    return LOGIN_UNKNOWN_ERROR


def TestToken():
    # Load credentials from the file
    credentials = ReadCredentials()
    ACCES_TOKEN = credentials.get('DEFAULT','access_token', fallback= None)
    if not ACCES_TOKEN:
        return False
    HEADERS['Authorization'] = f"Bearer {ACCES_TOKEN}"

    try:
        response = requests.get(TEST_URL, headers=HEADERS)
        if response.status_code == 200:
            logger.log_info("Test completed successfully")
            data = response.json()
            devices = data.get("devices", [])
            if devices:
                # Extract the dev_access_code and dev_id from the first device
                dev_access_code = devices[0].get("dev_access_code")
                dev_id = devices[0].get("dev_id")

                # Save these values to the credentials file
                if dev_access_code and dev_id:
                    SaveNewToken("dev_acces_code", dev_access_code)
                    SaveNewToken("dev_id", dev_id)
            return True
        else:
            logger.log_error(f"Failed to test the access code {response.status_code}: {response.text}")
    except Exception as e:
        logger.log_exception(e)
    return False

