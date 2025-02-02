import traceback
import time

def log_error(error_message):
    """Logs errors to log_errors.txt"""
    with open("log_errors.txt", "a") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {error_message}\n")
    time.sleep(10) # Wait 10 seconds