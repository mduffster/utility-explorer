"""SQLite database for local storage."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from ue.config import DB_PATH, ensure_data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS inbox_items (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,  -- gmail, calendar, slack, twitter, linkedin
    item_type TEXT NOT NULL,  -- email, event, dm, mention, etc.
    sender TEXT,
    subject TEXT,
    snippet TEXT,
    timestamp TEXT NOT NULL,
    workstream TEXT,  -- ai-research, terrasol, blog, consulting, or NULL
    needs_response INTEGER DEFAULT 0,
    responded INTEGER DEFAULT 0,
    raw_data TEXT,  -- JSON blob of full item
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_type TEXT NOT NULL,  -- email_sent, commit, doc_created, application, win
    description TEXT NOT NULL,
    workstream TEXT,
    source TEXT,  -- gmail, git, manual, etc.
    metadata TEXT,  -- JSON blob
    timestamp TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS block_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_name TEXT NOT NULL,  -- e.g., "Workout", "Dog Walk", "AI Research"
    date TEXT NOT NULL,  -- YYYY-MM-DD
    status TEXT NOT NULL,  -- completed, skipped, partial
    reason TEXT,  -- why skipped/partial
    notes TEXT,
    duration_minutes INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(block_name, date)
);

CREATE TABLE IF NOT EXISTS block_targets (
    block_name TEXT PRIMARY KEY,
    weekly_target INTEGER DEFAULT 0,  -- 0 = daily, N = N times per week
    workstream TEXT,  -- which workstream this belongs to
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    due_date TEXT,  -- YYYY-MM-DD, NULL if no deadline
    workstream TEXT,
    priority TEXT DEFAULT 'normal',  -- low, normal, high
    status TEXT DEFAULT 'pending',  -- pending, done, cancelled
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_inbox_source ON inbox_items(source);
CREATE INDEX IF NOT EXISTS idx_inbox_timestamp ON inbox_items(timestamp);
CREATE INDEX IF NOT EXISTS idx_inbox_needs_response ON inbox_items(needs_response);
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_log(activity_type);
CREATE INDEX IF NOT EXISTS idx_block_completions_date ON block_completions(date);
CREATE INDEX IF NOT EXISTS idx_block_completions_name ON block_completions(block_name);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
"""


def get_db() -> sqlite3.Connection:
    """Get database connection, creating schema if needed."""
    ensure_data_dir()
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def upsert_inbox_item(
    id: str,
    source: str,
    item_type: str,
    timestamp: str,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    snippet: Optional[str] = None,
    workstream: Optional[str] = None,
    needs_response: bool = False,
    raw_data: Optional[str] = None,
):
    """Insert or update an inbox item."""
    db = get_db()
    db.execute(
        """
        INSERT INTO inbox_items (id, source, item_type, sender, subject, snippet,
                                  timestamp, workstream, needs_response, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            sender = excluded.sender,
            subject = excluded.subject,
            snippet = excluded.snippet,
            timestamp = excluded.timestamp,
            raw_data = excluded.raw_data
        """,
        (id, source, item_type, sender, subject, snippet, timestamp,
         workstream, int(needs_response), raw_data),
    )
    db.commit()
    db.close()


def activity_exists(source: str, metadata_key: str, metadata_value: str) -> bool:
    """Check if an activity with matching source and metadata key/value exists."""
    import json as json_mod
    db = get_db()
    rows = db.execute(
        "SELECT metadata FROM activity_log WHERE source = ?",
        (source,),
    ).fetchall()
    db.close()

    for row in rows:
        if row["metadata"]:
            try:
                meta = json_mod.loads(row["metadata"])
                if meta.get(metadata_key) == metadata_value:
                    return True
            except Exception:
                pass
    return False


def log_activity(
    activity_type: str,
    description: str,
    timestamp: Optional[str] = None,
    workstream: Optional[str] = None,
    source: Optional[str] = None,
    metadata: Optional[str] = None,
):
    """Log an activity."""
    db = get_db()
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    db.execute(
        """
        INSERT INTO activity_log (activity_type, description, workstream, source, metadata, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (activity_type, description, workstream, source, metadata, timestamp),
    )
    db.commit()
    db.close()


def get_inbox_items(
    source: Optional[str] = None,
    needs_response: Optional[bool] = None,
    workstream: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Get inbox items with optional filters."""
    db = get_db()
    query = "SELECT * FROM inbox_items WHERE 1=1"
    params = []

    if source:
        query += " AND source = ?"
        params.append(source)
    if needs_response is not None:
        query += " AND needs_response = ?"
        params.append(int(needs_response))
    if workstream:
        query += " AND workstream = ?"
        params.append(workstream)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_activity(
    activity_type: Optional[str] = None,
    since: Optional[str] = None,
    workstream: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Get activity log with optional filters."""
    db = get_db()
    query = "SELECT * FROM activity_log WHERE 1=1"
    params = []

    if activity_type:
        query += " AND activity_type = ?"
        params.append(activity_type)
    if since:
        query += " AND timestamp >= ?"
        params.append(since)
    if workstream:
        query += " AND workstream = ?"
        params.append(workstream)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(row) for row in rows]


def log_block_completion(
    block_name: str,
    date: str,
    status: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    duration_minutes: Optional[int] = None,
):
    """Log a block completion (completed, skipped, partial)."""
    db = get_db()
    db.execute(
        """
        INSERT INTO block_completions (block_name, date, status, reason, notes, duration_minutes)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(block_name, date) DO UPDATE SET
            status = excluded.status,
            reason = excluded.reason,
            notes = excluded.notes,
            duration_minutes = excluded.duration_minutes
        """,
        (block_name, date, status, reason, notes, duration_minutes),
    )
    db.commit()
    db.close()


def set_block_target(block_name: str, weekly_target: int, workstream: Optional[str] = None):
    """Set a weekly target for a block (0 = daily)."""
    db = get_db()
    db.execute(
        """
        INSERT INTO block_targets (block_name, weekly_target, workstream)
        VALUES (?, ?, ?)
        ON CONFLICT(block_name) DO UPDATE SET
            weekly_target = excluded.weekly_target,
            workstream = excluded.workstream
        """,
        (block_name, weekly_target, workstream),
    )
    db.commit()
    db.close()


def get_block_targets() -> list[dict]:
    """Get all active block targets."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM block_targets WHERE is_active = 1"
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_block_completions(
    block_name: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Get block completions with optional filters."""
    db = get_db()
    query = "SELECT * FROM block_completions WHERE 1=1"
    params = []

    if block_name:
        query += " AND block_name = ?"
        params.append(block_name)
    if since:
        query += " AND date >= ?"
        params.append(since)

    query += " ORDER BY date DESC, block_name LIMIT ?"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_week_block_summary(block_name: str) -> dict:
    """Get this week's completion count for a block."""
    db = get_db()
    from datetime import timedelta
    from ue.utils.dates import get_effective_date

    # Get start of current week (Monday), using effective date (2am boundary)
    today = get_effective_date()
    week_start = today - timedelta(days=today.weekday())

    row = db.execute(
        """
        SELECT COUNT(*) as completed
        FROM block_completions
        WHERE block_name = ? AND date >= ? AND status = 'completed'
        """,
        (block_name, week_start.isoformat()),
    ).fetchone()

    target_row = db.execute(
        "SELECT weekly_target FROM block_targets WHERE block_name = ?",
        (block_name,)
    ).fetchone()

    db.close()

    return {
        "block_name": block_name,
        "completed": row["completed"] if row else 0,
        "target": target_row["weekly_target"] if target_row else 0,
    }


def add_task(
    title: str,
    due_date: Optional[str] = None,
    workstream: Optional[str] = None,
    priority: str = "normal",
    notes: Optional[str] = None,
) -> int:
    """Add a task. Returns the task ID."""
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO tasks (title, due_date, workstream, priority, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, due_date, workstream, priority, notes),
    )
    task_id = cursor.lastrowid
    db.commit()
    db.close()
    return task_id


def complete_task(task_id: int):
    """Mark a task as done."""
    db = get_db()
    db.execute(
        "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ?",
        (datetime.now().isoformat(), task_id),
    )
    db.commit()
    db.close()


def cancel_task(task_id: int):
    """Cancel a task."""
    db = get_db()
    db.execute("UPDATE tasks SET status = 'cancelled' WHERE id = ?", (task_id,))
    db.commit()
    db.close()


def update_task(
    task_id: int,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
    workstream: Optional[str] = None,
    priority: Optional[str] = None,
    notes: Optional[str] = None,
    clear_due: bool = False,
    clear_workstream: bool = False,
) -> bool:
    """Update a task. Only updates fields that are provided.

    Use clear_due=True to remove the due date.
    Use clear_workstream=True to remove the workstream.
    Returns True if task was found and updated.
    """
    db = get_db()

    # Build update query dynamically
    updates = []
    params = []

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)
    elif clear_due:
        updates.append("due_date = NULL")
    if workstream is not None:
        updates.append("workstream = ?")
        params.append(workstream)
    elif clear_workstream:
        updates.append("workstream = NULL")
    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)

    if not updates:
        db.close()
        return False

    params.append(task_id)
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    cursor = db.execute(query, params)
    db.commit()
    updated = cursor.rowcount > 0
    db.close()
    return updated


def get_task(task_id: int) -> Optional[dict]:
    """Get a single task by ID."""
    db = get_db()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_tasks(
    status: str = "pending",
    workstream: Optional[str] = None,
    include_overdue: bool = True,
) -> list[dict]:
    """Get tasks, sorted by due date."""
    db = get_db()
    query = "SELECT * FROM tasks WHERE status = ?"
    params = [status]

    if workstream:
        query += " AND workstream = ?"
        params.append(workstream)

    query += " ORDER BY due_date IS NULL, due_date ASC, priority DESC"

    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_upcoming_tasks(days: int = 7) -> list[dict]:
    """Get pending tasks due in the next N days."""
    db = get_db()
    today = datetime.now().date()
    future = today + __import__("datetime").timedelta(days=days)

    rows = db.execute(
        """
        SELECT * FROM tasks
        WHERE status = 'pending'
        AND due_date IS NOT NULL
        AND due_date <= ?
        ORDER BY due_date ASC
        """,
        (future.isoformat(),),
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_overdue_tasks() -> list[dict]:
    """Get pending tasks that are past due."""
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    rows = db.execute(
        """
        SELECT * FROM tasks
        WHERE status = 'pending'
        AND due_date IS NOT NULL
        AND due_date < ?
        ORDER BY due_date ASC
        """,
        (today,),
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_tasks_completed_since(since: str) -> list[dict]:
    """Get tasks completed since a given date."""
    db = get_db()
    rows = db.execute(
        """
        SELECT * FROM tasks
        WHERE status = 'done'
        AND completed_at >= ?
        ORDER BY completed_at DESC
        """,
        (since,),
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_tasks_created_since(since: str) -> list[dict]:
    """Get all tasks created since a given date."""
    db = get_db()
    rows = db.execute(
        """
        SELECT * FROM tasks
        WHERE created_at >= ?
        ORDER BY created_at DESC
        """,
        (since,),
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_block_completions_range(start: str, end: str) -> list[dict]:
    """Get block completions within a date range (inclusive)."""
    db = get_db()
    rows = db.execute(
        """
        SELECT * FROM block_completions
        WHERE date >= ? AND date <= ?
        ORDER BY date DESC, block_name
        """,
        (start, end),
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]
