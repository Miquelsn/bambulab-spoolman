import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from BambuPrinter.task_validation import filter_saved_tasks


DATABASE_PATH = os.environ.get(
    "BAMBU_SPOOLMAN_DATABASE",
    str(Path("data") / "bambulab_spoolman.sqlite3"),
)
LEGACY_TASK_PATH = "task.txt"

_database_lock = threading.RLock()


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _make_private(path):
    if os.name != "posix":
        return
    parent = os.path.dirname(path)
    if parent:
        os.chmod(parent, 0o700)
    os.chmod(path, 0o600)


def _connect(database_path=None):
    path = database_path or DATABASE_PATH
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, mode=0o700, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            history_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.commit()
    _make_private(path)
    return connection


def _normalise_task(task, history_id=None):
    saved = dict(task)
    saved["history_id"] = str(history_id or saved.get("history_id") or uuid.uuid4())
    return saved


def _migrate_legacy_tasks(connection, legacy_path=None):
    legacy_path = legacy_path or LEGACY_TASK_PATH
    marker = connection.execute(
        "SELECT value FROM metadata WHERE key = 'legacy_task_migration'"
    ).fetchone()
    if marker is not None:
        return 0

    tasks = []
    try:
        with open(legacy_path, "r", encoding="utf-8") as task_file:
            tasks = filter_saved_tasks(json.load(task_file))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        tasks = []

    now = _utc_now()
    imported = 0
    for position, task in enumerate(tasks):
        # Stable IDs prevent duplicate imports if a migration is interrupted.
        legacy_key = json.dumps(task, sort_keys=True, separators=(",", ":"))
        history_id = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"legacy-task:{position}:{legacy_key}")
        )
        saved = _normalise_task(task, history_id)
        connection.execute(
            """
            INSERT OR IGNORE INTO tasks(history_id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (history_id, json.dumps(saved), now, now),
        )
        imported += 1

    connection.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
        ("legacy_task_migration", now),
    )
    connection.commit()
    return imported


def save_task(task, database_path=None, legacy_path=None):
    saved = _normalise_task(task)
    now = _utc_now()
    with _database_lock, _connect(database_path) as connection:
        _migrate_legacy_tasks(connection, legacy_path)
        connection.execute(
            """
            INSERT INTO tasks(history_id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(history_id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (saved["history_id"], json.dumps(saved), now, now),
        )
        connection.commit()
    return saved


def load_tasks(database_path=None, legacy_path=None):
    with _database_lock, _connect(database_path) as connection:
        _migrate_legacy_tasks(connection, legacy_path)
        rows = connection.execute(
            "SELECT payload FROM tasks ORDER BY created_at ASC, rowid ASC"
        ).fetchall()

    tasks = []
    for row in rows:
        try:
            task = json.loads(row["payload"])
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(task, dict):
            tasks.append(task)
    return filter_saved_tasks(tasks)


def get_task(history_id, database_path=None, legacy_path=None):
    with _database_lock, _connect(database_path) as connection:
        _migrate_legacy_tasks(connection, legacy_path)
        row = connection.execute(
            "SELECT payload FROM tasks WHERE history_id = ?",
            (str(history_id),),
        ).fetchone()
    if row is None:
        return None
    try:
        task = json.loads(row["payload"])
    except (TypeError, json.JSONDecodeError):
        return None
    return task if isinstance(task, dict) else None


def update_task(history_id, update, database_path=None, legacy_path=None):
    """Atomically update one task using a callable and return the saved record."""
    with _database_lock, _connect(database_path) as connection:
        _migrate_legacy_tasks(connection, legacy_path)
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT payload FROM tasks WHERE history_id = ?",
            (str(history_id),),
        ).fetchone()
        if row is None:
            connection.rollback()
            raise KeyError(f"Unknown task history ID: {history_id}")

        task = json.loads(row["payload"])
        updated = update(dict(task))
        if not isinstance(updated, dict):
            connection.rollback()
            raise TypeError("Task update must return a dictionary")
        updated["history_id"] = str(history_id)
        connection.execute(
            "UPDATE tasks SET payload = ?, updated_at = ? WHERE history_id = ?",
            (json.dumps(updated), _utc_now(), str(history_id)),
        )
        connection.commit()
        return updated
