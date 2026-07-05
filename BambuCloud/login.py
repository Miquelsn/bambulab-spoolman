import requests
from helper_logs import logger
from tools import DeleteToken, ReadCredentials, SaveNewToken, SavePrinterDevices

# API endpoint for login and sending the verification code
LOGIN_URL = "https://api.bambulab.com/v1/user-service/user/login"
SEND_CODE_URL = "https://api.bambulab.com/v1/user-service/user/sendemail/code"
TEST_URL = "https://api.bambulab.com/v1/iot-service/api/user/bind"
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


def SendVerificationCode():
    # Load credentials from the file
    credentials = ReadCredentials()
    email = credentials.get("DEFAULT", "email", fallback=None)

    if not email:
        logger.log_error("Missing email in credentials file.")
        return False

    """Send a verification code to the user's email."""
    payload = {"email": email, "type": "codeLogin"}

    try:
        response = requests.post(
            SEND_CODE_URL,
            headers=HEADERS,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            logger.log_info("Verification code sent to your email.")
            return True
        else:
            logger.log_error(
                f"Failed to send verification code (HTTP {response.status_code})."
            )
    except requests.RequestException as error:
        logger.log_exception(error)
    return False


def _login_result(status, message, access_token=None):
    result = {"status": status, "message": message}
    if access_token:
        result["access_token"] = access_token
    return result


def LoginWithCredentials(email, password):
    """Start a GUI-driven login without reading from standard input."""
    email = str(email or "").strip()
    password = str(password or "")
    if not email or not password:
        return _login_result(
            "bad_credentials", "Enter both your Bambu Cloud email and password."
        )

    SaveNewToken("email", email)
    DeleteToken("password")
    initial_payload = {"account": email, "password": password}

    try:
        response = requests.post(
            LOGIN_URL,
            headers=HEADERS,
            json=initial_payload,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("accessToken")
            if access_token:
                logger.log_info("Login successful!")
                SaveNewToken("access_token", access_token)
                DeleteToken("password")
                TestToken()
                return _login_result(
                    "success", "Connected to Bambu Cloud.", access_token
                )
            if data.get("loginType") == "verifyCode":
                if SendVerificationCode():
                    return _login_result(
                        "needs_verification_code",
                        "Enter the verification code sent to your email.",
                    )
                return _login_result(
                    "network_error", "The verification email could not be sent."
                )
            logger.log_error("Failed to retrieve tokens for unknown reason.")
            return _login_result("error", "Bambu Cloud did not return a token.")
        else:
            logger.log_error(f"Login failed (HTTP {response.status_code}).")
            status = (
                "bad_credentials"
                if response.status_code in (400, 401, 403)
                else "error"
            )
            return _login_result(
                status, f"Bambu Cloud login failed (HTTP {response.status_code})."
            )

    except (requests.RequestException, ValueError) as error:
        logger.log_exception(error)
        return _login_result("network_error", "Bambu Cloud could not be reached.")

    return _login_result("error", "Bambu Cloud login failed.")


def SubmitVerificationCode(email, verification_code):
    """Finish a GUI-driven verification-code login."""
    email = str(email or "").strip()
    verification_code = str(verification_code or "").strip()
    if not email or not verification_code:
        return _login_result(
            "invalid_verification_code", "Enter the verification code from your email."
        )

    try:
        response = requests.post(
            LOGIN_URL,
            headers=HEADERS,
            json={"account": email, "code": verification_code},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            logger.log_error(f"Verification failed (HTTP {response.status_code}).")
            return _login_result(
                "invalid_verification_code",
                "The verification code was rejected. Request a new code and try again.",
            )

        access_token = response.json().get("accessToken")
        if not access_token:
            return _login_result(
                "invalid_verification_code", "Bambu Cloud did not return a token."
            )

        SaveNewToken("email", email)
        SaveNewToken("access_token", access_token)
        DeleteToken("password")
        logger.log_info("Login successful after verification!")
        TestToken()
        return _login_result("success", "Connected to Bambu Cloud.", access_token)
    except (requests.RequestException, ValueError) as error:
        logger.log_exception(error)
        return _login_result("network_error", "Bambu Cloud could not be reached.")


def LoginAndGetToken(email=None, password=None):
    """Backward-compatible non-interactive login entry point."""
    credentials = ReadCredentials()
    legacy_password = credentials.get("DEFAULT", "password", fallback=None)
    if legacy_password:
        DeleteToken("password")
    if email is None:
        email = credentials.get("DEFAULT", "email", fallback="")
    if password is None:
        password = legacy_password
    result = LoginWithCredentials(email, password)
    return result.get("access_token")


def TestToken():
    # Load credentials from the file
    credentials = ReadCredentials()
    access_token = credentials.get("DEFAULT", "access_token", fallback=None)
    if not access_token:
        return False
    headers = dict(HEADERS)
    headers["Authorization"] = f"Bearer {access_token}"

    try:
        response = requests.get(TEST_URL, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            logger.log_info("Test completed successfully")
            DeleteToken("password")
            data = response.json()
            devices = data.get("devices", [])
            if devices:
                SavePrinterDevices(devices)
                logger.log_info(f"Discovered {len(devices)} Bambu Lab printer(s).")
            else:
                logger.log_error("No printers are bound to this Bambu Lab account.")
            return True
        else:
            logger.log_error(
                f"Bambu Cloud token validation failed (HTTP {response.status_code})."
            )
            if response.status_code in (401, 403):
                DeleteToken("access_token")
    except (requests.RequestException, ValueError) as error:
        logger.log_exception(error)
    return False
