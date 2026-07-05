import json
import time
from datetime import datetime
from enum import Enum

import BambuCloud.projects
from BambuPrinter.print_task import PrintTask
from helper_logs import logger


class State(Enum):
    IDLE = 0
    PREPARING = 1
    PRINTING = 2
    FAILED = 3
    UNKNOWN = 4
    UNKWON = 4  # Backward-compatible alias for the original typo.


class BambuPrinter:
    def __init__(self, printer_id=None, printer_name=None, printer_model=None):
        self.printer_id = printer_id
        self.printer_name = printer_name or printer_id or "Bambu printer"
        self.printer_model = printer_model
        self.current_state = State.UNKNOWN
        self.new_state = State.UNKNOWN
        self.current_gcode = None
        self.current_filament = None
        self.current_percent = 0
        self.print_task = PrintTask(
            printer_id=printer_id,
            printer_name=self.printer_name,
            printer_model=printer_model,
        )
        self.first_time = True
        self.complete_task = False
        self.externalFilamentID = None
        self.external_filaments = {}
        self.ams_filaments = {}
        self.active_filament_id = None
        self._last_task_lookup_id = None
        self._last_task_lookup_at = 0.0

    def _prefix(self, message):
        return f"[{self.printer_name}] {message}"

    @staticmethod
    def _filament_id(value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def ProcessMQTTMessage(self, msg):
        data = msg.payload.decode("utf-8")
        parsed_data = json.loads(data)
        print_data = parsed_data.get("print")
        if not isinstance(print_data, dict):
            return

        # Parse inventory before task metadata so an unassigned cloud filament
        # can be resolved against the active AMS/external tray.
        if "ams" in print_data:
            self.AMSFilamentParser(print_data["ams"])
        if "vt_tray" in print_data:
            self.ExternalFilamentParser(print_data["vt_tray"])
        if "mc_percent" in print_data:
            self.SetPrintPercentatge(print_data["mc_percent"])
        # The final payload can contain both an idle stage and FINISH/CANCELLED.
        # Process the authoritative gcode result first so the idle stage cannot
        # save a cancelled task as complete or save a completed task at 99%.
        if "gcode_state" in print_data:
            self.SetGcodeState(print_data["gcode_state"])
        if "stg_cur" in print_data:
            self.SetCurrentState(print_data["stg_cur"])
        if "task_id" in print_data and (
            self.complete_task
            or self.current_state in (State.PREPARING, State.PRINTING)
            or self.new_state in (State.PREPARING, State.PRINTING)
        ):
            self.SetWeightDetail(print_data["task_id"])

    def ProccessMQTTMsg(self, msg):
        """Backward-compatible alias for the original misspelled method."""
        return self.ProcessMQTTMessage(msg)

    def AMSFilamentParser(self, msg):
        if isinstance(msg, list):
            units = msg
            status = {}
        elif isinstance(msg, dict):
            units = msg.get("ams", [])
            status = msg
        else:
            return

        for unit in units or []:
            if not isinstance(unit, dict):
                continue
            try:
                ams_id = int(unit.get("id", 0))
            except (TypeError, ValueError):
                ams_id = 0
            for tray in unit.get("tray", []) or []:
                if not isinstance(tray, dict):
                    continue
                try:
                    tray_id = int(tray.get("id", 0))
                except (TypeError, ValueError):
                    continue
                filament_id = self._filament_id(tray.get("tray_info_idx"))
                if filament_id:
                    self.ams_filaments[ams_id * 4 + tray_id] = filament_id

        tray_now = status.get("tray_now")
        try:
            tray_now = int(tray_now)
        except (TypeError, ValueError):
            tray_now = None
        if tray_now == 254 and self.externalFilamentID:
            self.active_filament_id = self.externalFilamentID
        elif tray_now in self.ams_filaments:
            self.active_filament_id = self.ams_filaments[tray_now]

    def ExternalFilamentParser(self, msg):
        trays = msg if isinstance(msg, list) else [msg]
        for position, tray in enumerate(trays):
            if not isinstance(tray, dict):
                continue
            filament_id = self._filament_id(tray.get("tray_info_idx"))
            if not filament_id:
                continue
            tray_id = str(tray.get("id", position))
            self.external_filaments[tray_id] = filament_id
            self.externalFilamentID = filament_id

        # A single external path is unambiguous. For H2-series payloads with
        # multiple paths, the task mapping/active tray must select one.
        if len(self.external_filaments) == 1:
            self.active_filament_id = next(iter(self.external_filaments.values()))

    def _resolve_unassigned_filament(self, mapping):
        mapping = mapping if isinstance(mapping, dict) else {}

        ams_id = mapping.get("amsId", mapping.get("ams_id"))
        tray_id = mapping.get(
            "trayId",
            mapping.get("tray_id", mapping.get("slotId", mapping.get("slot_id"))),
        )
        if ams_id is not None and tray_id is not None:
            try:
                filament_id = self.ams_filaments.get(int(ams_id) * 4 + int(tray_id))
                if filament_id:
                    return filament_id
            except (TypeError, ValueError):
                pass

        global_slot = mapping.get("amsSlot", mapping.get("ams_slot"))
        if global_slot is not None:
            try:
                filament_id = self.ams_filaments.get(int(global_slot))
                if filament_id:
                    return filament_id
            except (TypeError, ValueError):
                pass

        if self.active_filament_id:
            return self.active_filament_id
        if len(self.external_filaments) == 1:
            return next(iter(self.external_filaments.values()))
        return None

    @staticmethod
    def _number(value, default=0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def SetWeightDetail(self, task_id):
        task_id = str(task_id).strip()
        if not task_id:
            return
        if task_id == "0":
            logger.log_error(
                self._prefix(
                    "Task ID is 0; filament usage requires a cloud print task."
                ),
                event="task_metadata_unavailable",
                subsystem="printer",
                printer_id=self.printer_id,
            )
            return
        if (
            self.print_task.task_id == task_id
            and self.print_task.teoric_filaments is not None
        ):
            return

        now = time.monotonic()
        if (
            self._last_task_lookup_id == task_id
            and now - self._last_task_lookup_at < 60
        ):
            return
        self._last_task_lookup_id = task_id
        self._last_task_lookup_at = now

        self.print_task.task_id = task_id
        job_id = BambuCloud.projects.GetJobID(task_id)
        if job_id is None:
            return
        self.print_task.job_id = job_id
        task_detail = BambuCloud.projects.GetTaksDetail(job_id)
        if not isinstance(task_detail, dict):
            return

        self.print_task.total_weight = self._number(task_detail.get("weight"))
        self.print_task.model_name = task_detail.get("title")
        self.print_task.image_cover_url = task_detail.get("cover")

        filaments = []
        mappings = task_detail.get("amsDetailMapping") or []
        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue
            filament_id = self._filament_id(mapping.get("filamentId"))
            if not filament_id:
                filament_id = self._resolve_unassigned_filament(mapping)
                if filament_id:
                    logger.log_info(
                        self._prefix(
                            f"Resolved an unassigned cloud filament as {filament_id}."
                        ),
                        event="filament_resolved",
                        subsystem="printer",
                        printer_id=self.printer_id,
                        task_id=task_id,
                    )
                else:
                    logger.log_error(
                        self._prefix(
                            "Could not resolve an unassigned filament to an AMS or "
                            "external tray; its usage will not be sent to Spoolman."
                        ),
                        event="filament_resolution_failed",
                        subsystem="printer",
                        printer_id=self.printer_id,
                        task_id=task_id,
                    )
            filaments.append(
                {
                    "filamentId": filament_id,
                    "weight": self._number(mapping.get("weight")),
                }
            )

        if not filaments and self.print_task.total_weight > 0:
            filament_id = self._resolve_unassigned_filament({})
            if filament_id:
                filaments.append(
                    {
                        "filamentId": filament_id,
                        "weight": self.print_task.total_weight,
                    }
                )

        self.print_task.teoric_filaments = filaments

    def SetPrintPercentatge(self, percentage):
        self.current_percent = self._number(percentage)

    def SetCurrentState(self, state_id):
        try:
            state_id = int(state_id)
        except (TypeError, ValueError):
            return
        if state_id == 0:
            self.new_state = State.PRINTING
        elif state_id in (1, 2, 8) and self.current_state in (
            State.IDLE,
            State.UNKNOWN,
        ):
            self.new_state = State.PREPARING
        elif state_id == 255:
            self.new_state = State.IDLE
        else:
            return
        self.ComprobateState()

    def SetGcodeState(self, gcode):
        self.current_gcode = str(gcode).upper()
        if self.current_gcode in ("FAILED", "CANCELLED"):
            self.new_state = State.FAILED
        elif self.current_gcode in ("PREPARE", "SLICING"):
            self.new_state = State.PREPARING
        elif self.current_gcode in ("RUNNING", "PRINTING", "PAUSE", "PAUSED"):
            self.new_state = State.PRINTING
        elif self.current_gcode == "FINISH":
            self.current_percent = 100
            self.new_state = State.IDLE
        elif self.current_gcode == "IDLE":
            self.new_state = State.IDLE
        else:
            return
        self.ComprobateState()

    def _begin_task(self):
        self.complete_task = True
        self.print_task.CleanTask()
        self._last_task_lookup_id = None
        self._last_task_lookup_at = 0.0
        self.print_task.start_time = datetime.now().strftime("%H:%M:%S-%d-%m-%Y")

    def _finish_task(self, status):
        self.print_task.percent_complete = self.current_percent
        self.print_task.status = status
        self.print_task.end_time = datetime.now().strftime("%H:%M:%S-%d-%m-%Y")
        if self.complete_task:
            self.print_task.ReportAndSaveTask()
        self.complete_task = False

    def ComprobateState(self):
        if self.first_time:
            self.first_time = False
            self.current_state = self.new_state
            if self.new_state in (State.PREPARING, State.PRINTING):
                self._begin_task()
                if self.new_state == State.PRINTING:
                    self.print_task.init_percent = self.current_percent
            return

        if self.current_state == self.new_state:
            return

        previous_state = self.current_state
        if self.new_state == State.IDLE:
            if previous_state == State.PRINTING:
                logger.log_info(
                    self._prefix("Print completed."),
                    event="print_completed",
                    subsystem="printer",
                    printer_id=self.printer_id,
                )
                self._finish_task("Complete")
            elif previous_state == State.PREPARING:
                self.complete_task = False
        elif self.new_state == State.PREPARING:
            logger.log_info(
                self._prefix("Printer is preparing."),
                event="printer_preparing",
                subsystem="printer",
                printer_id=self.printer_id,
            )
            self._begin_task()
        elif self.new_state == State.PRINTING:
            if previous_state != State.PREPARING:
                self._begin_task()
            self.print_task.init_percent = self.current_percent
            logger.log_info(
                self._prefix("Printer is printing."),
                event="printer_printing",
                subsystem="printer",
                printer_id=self.printer_id,
            )
        elif self.new_state == State.FAILED:
            logger.log_warning(
                self._prefix("Print failed or was cancelled."),
                event="print_failed",
                subsystem="printer",
                printer_id=self.printer_id,
            )
            if previous_state == State.PRINTING:
                self._finish_task("Failed")
            else:
                self.complete_task = False

        logger.log_info(
            self._prefix(
                f"State changed from {previous_state.name} to {self.new_state.name}."
            ),
            event="printer_state_changed",
            subsystem="printer",
            printer_id=self.printer_id,
            previous_state=previous_state.name,
            state=self.new_state.name,
        )
        self.current_state = self.new_state


# Kept for external users of the old module API. Multi-printer MQTT creates one
# BambuPrinter instance per configured device and does not use this singleton.
bambu_printer = BambuPrinter()
