import requests
import os
from tools import *
from helper_logs import logger

# API endpoint for login and sending the verification code
LOGIN_URL = "https://api.bambulab.com/v1/user-service/user/login"
SEND_CODE_URL = "https://api.bambulab.com/v1/user-service/user/sendemail/code"
TEST_URL = "https://api.bambulab.com/v1/iot-service/api/user/bind"


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

def LoginAndGetToken():
    # Load credentials from the file
    credentials = ReadCredentials()
    EMAIL = credentials.get('DEFAULT','email', fallback= None)
    PASSWORD = credentials.get('DEFAULT','password', fallback= None)

    # Ensure that the credentials are loaded correctly
    if not EMAIL:
        # If the credentials are missing, prompt the user to enter them
        EMAIL = input("Enter your email: ")
        SaveNewToken("email", EMAIL)

    if not PASSWORD:
        PASSWORD = input("Enter your password: ")
        SaveNewToken("password", PASSWORD)
        
    """Logs in and retrieves the access token."""
    initial_payload = {
        "account": EMAIL,
        "password": PASSWORD
    }

    try:
        response = requests.post(LOGIN_URL, headers=HEADERS, json=initial_payload)
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("accessToken")
            if access_token:
                logger.log_info("Login successful!")
                return 
            else:
                if data.get("loginType") == "verifyCode":
                    # Step 1: Send verification code
                    if SendVerificationCode():
                        # Step 2: Ask for the verification code
                        verification_code = input("Enter the verification code sent to your email: ")
                        # Retry login with the verification code
                        verification_payload = {
                            "account": EMAIL,
                            "code": verification_code
                        }
                        retry_response = requests.post(LOGIN_URL, headers=HEADERS, json=verification_payload)
                        if retry_response.status_code == 200:
                            retry_data = retry_response.json()
                            access_token = retry_data.get("accessToken")
                            if access_token:
                                logger.log_info("Login successful after verification!")
                                # Save the access token to the file
                                SaveNewToken("access_token", access_token)
                                return access_token
                            else:
                                logger.log_error("Failed to retrieve token after verification.")
                        else:
                            logger.log_error(f"Verification failed with status code {retry_response.status_code}: {retry_response.text}")
                else:
                    logger.log_error("Failed to retrieve tokens for unknown reason.")
        else:
            logger.log_error(f"Login failed with status code {response.status_code}: {response.text}")

    except Exception as e:
        logger.log_exception(e)

    return None

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

