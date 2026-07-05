from datetime import datetime, timezone

from BambuPrinter.task_repository import save_task
from BambuPrinter.task_validation import is_unknown_zero_weight_task
from helper_logs import logger

class PrintTask:
    def __init__(self, printer_id=None, printer_name=None, printer_model=None):
        self.history_id = None
        self.printer_id = printer_id
        self.printer_name = printer_name
        self.printer_model = printer_model
        self.model_name = None
        self.task_id = None
        self.job_id = None
        self.ams_mapping = None
        self.total_weight = 0
        self.start_time = None
        self.end_time = None
        self.teoric_filaments = None
        self.reported_filament = None
        self.init_percent = 0
        self.percent_complete = 0
        self.status = None
        self.image_cover_url = None

    def to_dict(self):
        """Convert the PrintTask object to a dictionary."""
        return {
            "history_id": self.history_id,
            "printer_id": self.printer_id,
            "printer_name": self.printer_name,
            "printer_model": self.printer_model,
            "model_name": self.model_name,
            "task_id": self.task_id,
            "job_id": self.job_id,
            "total_weight": self.total_weight,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "teoric_filaments": self.teoric_filaments,
            "reported_filament": self.reported_filament,
            "init_percent": self.init_percent,
            "percent_complete": self.percent_complete,
            "status": self.status,
            "image_cover_url": self.image_cover_url,
        }

    def CleanTask(self):
        """Reset print-specific fields while retaining printer identity."""
        self.history_id = None
        self.model_name = None
        self.task_id = None
        self.job_id = None
        self.ams_mapping = None
        self.total_weight = 0
        self.start_time = None
        self.end_time = None
        self.teoric_filaments = None
        self.reported_filament = None
        self.init_percent = 0
        self.percent_complete = 0
        self.status = None
        self.image_cover_url = None

    def ReportAndSaveTask(self):
        """Report filament consumption and save a structured task record."""
        if is_unknown_zero_weight_task(self.to_dict()):
            logger.log_info(
                "Skipping task with unknown model name and zero weight.",
                event="task_discarded",
                subsystem="tasks",
                printer_id=self.printer_id,
            )
            return False

        if self.percent_complete != 0 and self.teoric_filaments:
            # Lazy import keeps history validation usable without API dependencies.
            import Spoolman.spoolman_filament as spoolman_filament

            self.reported_filament = []
            if self.percent_complete == 100:
                multiplier = 1
            else:
                multiplier = max(
                    0,
                    min(1, (self.percent_complete - self.init_percent) / 100),
                )

            for filament in self.teoric_filaments:
                reported = dict(filament)
                reported["weight"] = multiplier * filament["weight"]
                result = spoolman_filament.RegisterFilamentUsage(
                    reported["filamentId"],
                    reported["weight"],
                    printer_id=self.printer_id,
                )
                reported.update(
                    {
                        key: value
                        for key, value in result.items()
                        if key != "success" and value is not None
                    }
                )
                reported["report_status"] = (
                    "reported" if result["success"] else "failed"
                )
                reported["reported_at"] = datetime.now(timezone.utc).isoformat()
                self.reported_filament.append(reported)

        saved = save_task(self.to_dict())
        self.history_id = saved["history_id"]
        logger.log_info(
            f"Saved task history for {self.model_name or 'unknown task'}.",
            event="task_saved",
            subsystem="tasks",
            printer_id=self.printer_id,
            task_id=self.history_id,
            model_name=self.model_name,
            status=self.status,
        )
        return True
