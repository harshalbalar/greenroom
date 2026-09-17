"""
Background task manager.

Uses Python's ThreadPoolExecutor + SQLite for task tracking.
No Redis or Celery needed for MVP. Upgrade path: swap executor
for Celery worker, keep the same task interface.

Usage:
    task_id = task_manager.submit("scan_and_score", my_function, arg1, arg2)
    status = task_manager.get_status(task_id)  # pending | running | completed | failed
"""

import uuid
import json
import threading
import traceback
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from database import engine
from sqlalchemy import text


# Simple SQLite task table (created on first use)
_init_lock = threading.Lock()
_initialized = False


def _ensure_table():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS background_tasks (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress TEXT DEFAULT '',
                    result TEXT,
                    error TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT
                )
            """))
            conn.commit()
        _initialized = True


class TaskManager:
    """Manages background tasks with a thread pool."""

    def __init__(self, max_workers: int = 3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        _ensure_table()

    def submit(self, task_type: str, fn, *args, **kwargs) -> str:
        """Submit a function to run in the background. Returns task_id."""
        task_id = uuid.uuid4().hex[:12]

        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO background_tasks (id, task_type, status, created_at)
                VALUES (:id, :type, 'pending', :now)
            """), {"id": task_id, "type": task_type, "now": datetime.now(timezone.utc).isoformat()})
            conn.commit()

        def wrapper():
            try:
                self._update(task_id, status="running", started_at=datetime.now(timezone.utc).isoformat())
                result = fn(*args, task_id=task_id, **kwargs)
                self._update(
                    task_id,
                    status="completed",
                    result=json.dumps(result) if result else None,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as e:
                self._update(
                    task_id,
                    status="failed",
                    error=f"{e}\n{traceback.format_exc()}",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )

        self.executor.submit(wrapper)
        return task_id

    def update_progress(self, task_id: str, message: str):
        """Update progress message for a running task (called from inside the task)."""
        self._update(task_id, progress=message)

    def get_status(self, task_id: str) -> dict | None:
        """Get current status of a task."""
        _ensure_table()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM background_tasks WHERE id = :id"),
                {"id": task_id},
            ).mappings().first()
            if not row:
                return None
            d = dict(row)
            if d.get("result"):
                try:
                    d["result"] = json.loads(d["result"])
                except json.JSONDecodeError:
                    pass
            return d

    def get_recent(self, limit: int = 10) -> list[dict]:
        """Get recent tasks."""
        _ensure_table()
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM background_tasks ORDER BY created_at DESC LIMIT :lim"),
                {"lim": limit},
            ).mappings().all()
            return [dict(r) for r in rows]

    def _update(self, task_id: str, **fields):
        """Update task fields in the database."""
        if not fields:
            return
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        fields["id"] = task_id
        with engine.connect() as conn:
            conn.execute(text(f"UPDATE background_tasks SET {sets} WHERE id = :id"), fields)
            conn.commit()


# Global singleton
task_manager = TaskManager()
