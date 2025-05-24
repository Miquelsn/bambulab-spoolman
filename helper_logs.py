# logger.py
import time
import threading
import traceback

class Logger:
    def __init__(self, log_file_path="app.log", max_lines=1000):
        self.log_file_path = log_file_path
        self.max_lines = max_lines
        self.lock = threading.Lock()
        self.logs = []
        self._load_existing_logs()

    def _load_existing_logs(self):
        try:
            with open(self.log_file_path, "r") as f:
                lines = f.readlines()
                self.logs = [line.strip() for line in lines[-self.max_lines:]]
        except FileNotFoundError:
            self.logs = []

    def _write_log(self, message: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{timestamp} - {message}"
        with self.lock:
            self.logs.append(log_line)
            if len(self.logs) > self.max_lines:
                self.logs.pop(0)
            with open(self.log_file_path, "a") as f:
                f.write(log_line + "\n")

    def log_info(self, message: str):
        self._write_log(f"INFO: {message}")

    def log_error(self, error: Exception):
        err_message = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        self._write_log(f"ERROR:\n{err_message}")

    def get_last_logs(self):
        with self.lock:
            return self.logs.copy()

# Create a global singleton instance of Logger
logger = Logger()
