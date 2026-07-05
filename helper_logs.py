import json
import os
import threading
import traceback
from datetime import datetime


def _timestamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _legacy_event(line):
    level = "info"
    message = line.strip()
    if " - ERROR:" in message:
        level = "error"
    elif " - EXCEPTION:" in message:
        level = "error"
    elif " - WARNING:" in message:
        level = "warning"
    timestamp = None
    if " - " in message:
        possible_timestamp, message = message.split(" - ", 1)
        timestamp = possible_timestamp.strip()
    for prefix in ("INFO: ", "ERROR: ", "WARNING: ", "EXCEPTION: "):
        if message.startswith(prefix):
            message = message[len(prefix) :]
            break
    return {
        "timestamp": timestamp or _timestamp(),
        "level": level,
        "event": "legacy_log",
        "subsystem": "service",
        "message": message,
    }


class Logger:
    """Thread-safe JSON-lines logger with a structured in-memory event feed."""

    def __init__(self, log_file_path="app.log", max_lines=1000, max_bytes=5_000_000):
        self.log_file_path = log_file_path
        self.max_lines = max_lines
        self.max_bytes = max_bytes
        self.lock = threading.Lock()
        self.logs = []
        self._load_existing_logs()

    def _load_existing_logs(self):
        try:
            with open(
                self.log_file_path, "r", encoding="utf-8", errors="replace"
            ) as log_file:
                lines = log_file.read().splitlines()[-self.max_lines :]
        except FileNotFoundError:
            lines = []

        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = _legacy_event(line)
            if isinstance(event, dict):
                self.logs.append(event)

    def _rotate_if_needed(self):
        try:
            if os.path.getsize(self.log_file_path) < self.max_bytes:
                return
            os.replace(self.log_file_path, f"{self.log_file_path}.1")
        except FileNotFoundError:
            pass

    def _write_log(
        self,
        level,
        message,
        *,
        event=None,
        subsystem="service",
        printer_id=None,
        task_id=None,
        **context,
    ):
        entry = {
            "timestamp": _timestamp(),
            "level": level,
            "event": event or "service_message",
            "subsystem": subsystem,
            "message": str(message),
        }
        if printer_id:
            entry["printer_id"] = str(printer_id)
        if task_id:
            entry["task_id"] = str(task_id)
        if context:
            entry["context"] = context

        with self.lock:
            self.logs.append(entry)
            if len(self.logs) > self.max_lines:
                self.logs.pop(0)
            self._rotate_if_needed()
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def log_info(self, message, **context):
        entry = self._write_log("info", message, **context)
        print(f"INFO: {entry['message']}")

    def log_warning(self, message, **context):
        entry = self._write_log("warning", message, **context)
        print(f"WARNING: {entry['message']}")

    def log_error(self, message, **context):
        entry = self._write_log("error", message, **context)
        print(f"ERROR: {entry['message']}")

    def log_exception(self, error, **context):
        stack_trace = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        entry = self._write_log(
            "error",
            str(error),
            event=context.pop("event", "unhandled_exception"),
            stack_trace=stack_trace,
            **context,
        )
        print(f"EXCEPTION: {entry['message']}\n{stack_trace}")

    def get_last_logs(self):
        with self.lock:
            return [dict(entry) for entry in self.logs]


logger = Logger()
