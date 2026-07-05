import re
from datetime import datetime, timezone

from BambuPrinter.task_repository import get_task, update_task


_FILAMENT_PATTERN = re.compile(
    r"^Filament Name: (?P<name>.*?), "
    r"Filament Type: (?P<type>.*?), "
    r"Filament Vendor: (?P<vendor>.*?), "
    r"Filament ID: (?P<id>[^,\s]+)\s*$"
)


def _load_catalog(path):
    catalog = {}
    try:
        with open(path, "r", encoding="utf-8") as filament_file:
            for line in filament_file:
                match = _FILAMENT_PATTERN.match(line.strip())
                if not match:
                    continue
                details = match.groupdict()
                filament_id = details.pop("id")
                catalog[str(filament_id)] = details
    except OSError:
        pass
    return catalog


def load_filament_catalog(path="slicer_filaments.txt"):
    """Load display metadata for Bambu filament profile IDs."""
    return _load_catalog(path)


def load_spool_catalog(path="spoolman_filaments.txt"):
    """Load cached Spoolman spool metadata keyed by physical spool ID."""
    return _load_catalog(path)


def _mapped_spool_id(mapping, printer_id, filament_id):
    if not filament_id:
        return None
    if printer_id:
        printer_key = f"{printer_id}::{filament_id}"
        if printer_key in mapping:
            return mapping[printer_key]
    return mapping.get(str(filament_id))


def _enrich_filament(
    filament,
    *,
    filament_catalog,
    spool_catalog,
    mapping,
    printer_id,
    is_reported,
):
    enriched = dict(filament)
    filament_id = str(filament.get("filamentId") or "")
    details = filament_catalog.get(filament_id)
    if details:
        enriched.setdefault("filament_name", details["name"])
        enriched.setdefault("filament_type", details["type"])
        enriched.setdefault("filament_vendor", details["vendor"])

    spool_id = enriched.get("spoolman_spool_id")
    if spool_id is None and is_reported:
        spool_id = _mapped_spool_id(mapping, printer_id, filament_id)
    if spool_id is not None:
        enriched["spoolman_spool_id"] = spool_id
        spool = spool_catalog.get(str(spool_id))
        if spool:
            enriched.setdefault("spoolman_spool_name", spool["name"])
            enriched.setdefault("spoolman_filament_type", spool["type"])
            enriched.setdefault("spoolman_vendor", spool["vendor"])
    if is_reported:
        enriched.setdefault("report_status", "reported")
    return enriched


def enrich_task_history(
    tasks,
    filament_catalog,
    spool_catalog=None,
    mapping=None,
):
    """Add display and reporting metadata without mutating saved records."""
    spool_catalog = spool_catalog or {}
    mapping = mapping or {}
    enriched_tasks = []
    for task in tasks:
        enriched_task = dict(task)
        printer_id = task.get("printer_id")
        for field_name in ("reported_filament", "teoric_filaments"):
            filaments = task.get(field_name)
            if not isinstance(filaments, list):
                continue
            enriched_task[field_name] = [
                _enrich_filament(
                    filament,
                    filament_catalog=filament_catalog,
                    spool_catalog=spool_catalog,
                    mapping=mapping,
                    printer_id=printer_id,
                    is_reported=field_name == "reported_filament",
                )
                for filament in filaments
                if isinstance(filament, dict)
            ]
        enriched_tasks.append(enriched_task)
    return enriched_tasks


def reassign_task_filament(history_id, filament_index, new_spool_id):
    """Move one task's recorded use to another physical Spoolman spool."""
    from Spoolman.spoolman_filament import (
        LoadFilamentMapping,
        ReassignFilamentUsage,
    )

    task = get_task(history_id)
    if task is None:
        raise ValueError("The selected task no longer exists.")

    reported = task.get("reported_filament")
    had_reported_usage = isinstance(reported, list) and bool(reported)
    if not had_reported_usage:
        theoretical = task.get("teoric_filaments")
        reported = [dict(item) for item in theoretical or [] if isinstance(item, dict)]
    if not isinstance(filament_index, int) or not 0 <= filament_index < len(reported):
        raise ValueError("The selected filament no longer exists.")

    filament = dict(reported[filament_index])
    try:
        weight = float(filament.get("weight") or 0)
    except (TypeError, ValueError) as error:
        raise ValueError("The selected filament has an invalid weight.") from error
    if weight <= 0:
        raise ValueError("The selected filament has no usage to report.")

    old_spool_id = filament.get("spoolman_spool_id")
    if old_spool_id is None and had_reported_usage:
        old_spool_id = _mapped_spool_id(
            LoadFilamentMapping(),
            task.get("printer_id"),
            filament.get("filamentId"),
        )
    if filament.get("report_status") == "failed":
        old_spool_id = None

    result = ReassignFilamentUsage(
        old_spool_id,
        new_spool_id,
        weight,
        printer_id=task.get("printer_id"),
    )
    if not result.get("success"):
        raise RuntimeError(result.get("error") or "Spoolman rejected the correction.")

    filament.update(
        {
            key: value
            for key, value in result.items()
            if key != "success" and value is not None
        }
    )
    filament["report_status"] = "corrected" if old_spool_id else "reported"
    filament["reported_at"] = datetime.now(timezone.utc).isoformat()
    if old_spool_id is not None:
        filament["previous_spoolman_spool_id"] = old_spool_id
    filament.pop("error", None)
    reported[filament_index] = filament

    def apply_update(saved_task):
        saved_task["reported_filament"] = reported
        return saved_task

    return update_task(history_id, apply_update)
