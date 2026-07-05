def is_unknown_zero_weight_task(task):
    """Return True for empty task records that should not be persisted."""
    model_name = task.get("model_name")
    normalized_name = str(model_name or "").strip().casefold()

    try:
        total_weight = float(task.get("total_weight") or 0)
    except (TypeError, ValueError):
        return False

    return normalized_name in {"", "unknown"} and total_weight == 0


def filter_saved_tasks(tasks):
    """Return saved task dictionaries, excluding invalid empty records."""
    if not isinstance(tasks, list):
        return []

    return [
        task
        for task in tasks
        if isinstance(task, dict) and not is_unknown_zero_weight_task(task)
    ]
