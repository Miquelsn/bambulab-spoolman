import requests
import os
from tools import *
from helper_logs import logger

# API endpoints
LOGIN_URL = "https://api.bambulab.com/v1/user-service/user/login"
TFA_URL   = "https://bambulab.com/api/sign-in/tfa"
SEND_CODE_URL = "https://api.bambulab.com/v1/user-service/user/sendemail/code"
TEST_URL = "https://api.bambulab.com/v1/iot-service/api/user/bind"

# Consent body required by the TFA endpoint (mirrors what the Bambu web client sends)
_CONSENT_BODY = '{"version":1,"scene":"login","formList":[{"formId":"TOU","op":"Opt-in"},{"formId":"PrivacyPolicy","op":"Opt-in"}]}'

LOGIN_SUCCESS = "success"
LOGIN_BAD_CREDENTIALS = "bad_credentials"
LOGIN_NEEDS_CODE = "needs_verification_code"
LOGIN_NEEDS_TFA = "needs_tfa"
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

# Headers that mirror the Bambu web client for the TFA endpoint (bambulab.com).
TFA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "X-BBL-Webview-Kind": "native",
    "Referer": "https://bambulab.com/en",
    "Origin": "https://bambulab.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

def SendVerificationCode():
    """Request an email verification code (new-device / suspicious-login flow)."""
    credentials = ReadCredentials()
    EMAIL = credentials.get('DEFAULT', 'email', fallback=None)

    if not EMAIL:
        logger.log_error("Missing email in credentials file.")
        return False

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
            logger.log_error(f"Failed to send verification code: {response.status_code} {response.text}")
    except Exception as e:
        logger.log_exception(e)
    return False



def LoginAndGetToken(verification_code=None, tfa_key=None):
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

    # Email verification code flow
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

    # Email verification code required
    if data.get("loginType") == "verifyCode":
        logger.log_info("Verification code required")
        if SendVerificationCode():
            return LOGIN_NEEDS_CODE
        else:
            return LOGIN_NETWORK_ERROR

    # Two-factor authentication (TOTP authenticator app) required
    if data.get("loginType") == "tfa":
        tfa_key = data.get("tfaKey", "")
        logger.log_info("TFA authentication required")
        # Return tuple so caller can forward the tfaKey to the frontend
        return LOGIN_NEEDS_TFA, tfa_key

    logger.log_error(f"Unknown login response: {data}")
    return LOGIN_UNKNOWN_ERROR


def SubmitTfaCode(tfa_key, tfa_code):
    """Submit a TOTP code to complete TFA login.

    Tries the OrcaSlicer API endpoint first (api.bambulab.com) with the
    correct 'tfaCode' field name.  Falls back to the Bambu web endpoint
    (bambulab.com/api/sign-in/tfa) if the API endpoint rejects the request.
    """
    credentials = ReadCredentials()
    EMAIL = credentials.get('DEFAULT', 'email', fallback=None)
    if not EMAIL:
        logger.log_error("Missing email in credentials file.")
        return LOGIN_BAD_CREDENTIALS

    # --- Attempt 1: API endpoint (no Cloudflare cookies needed) ---
    api_payload = {
        "account": EMAIL,
        "tfaCode": tfa_code,
        "tfaKey": tfa_key,
    }
    try:
        response = requests.post(LOGIN_URL, headers=HEADERS, json=api_payload, timeout=15)
        logger.log_info(f"TFA API response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("accessToken")
            if access_token:
                SaveNewToken("access_token", access_token)
                logger.log_info("TFA login successful via API endpoint")
                return LOGIN_SUCCESS
    except requests.exceptions.RequestException as e:
        logger.log_exception(e)

    # --- Attempt 2: Web endpoint (mirrors what the Bambu web client sends) ---
    web_payload = {
        "tfaKey": tfa_key,
        "tfaCode": tfa_code,
        "consentBody": _CONSENT_BODY,
    }
    try:
        response = requests.post(TFA_URL, headers=TFA_HEADERS, json=web_payload, timeout=15)
        logger.log_info(f"TFA web response: {response.status_code}")
        if response.status_code == 200:
            # Token is returned via Set-Cookie, not in the JSON body
            access_token = response.cookies.get("token")
            if access_token:
                SaveNewToken("access_token", access_token)
                logger.log_info("TFA login successful via web endpoint")
                return LOGIN_SUCCESS
            logger.log_error(f"TFA web 200 but no token cookie found. Body: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.log_exception(e)

    logger.log_error("TFA login failed on both API and web endpoints")
    return LOGIN_BAD_CREDENTIALS


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

