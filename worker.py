"""
Background task manager.

Uses Python's ThreadPoolExecutor + SQLAlchemy for task tracking.
No Redis or Celery needed for MVP. Upgrade path: swap executor
for Celery worker, keep the same task interface.

Usage:
    task_id = task_manager.submit("scan_and_score", my_function, arg1, arg2)
    status = task_manager.get_status(task_id)  # pending | running | completed | failed
"""

import uuid
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from database import SessionLocal, BackgroundTask, utcnow


class TaskManager:
    """Manages background tasks with a thread pool."""

    def __init__(self, max_workers: int = 3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, task_type: str, fn, *args, **kwargs) -> str:
        """Submit a function to run in the background. Returns task_id."""
        task_id = uuid.uuid4().hex[:12]

        with SessionLocal() as session:
            task = BackgroundTask(
                id=task_id,
                task_type=task_type,
                status="pending",
                created_at=utcnow(),
            )
            session.add(task)
            session.commit()

        def wrapper():
            try:
                self._update(task_id, status="running", started_at=utcnow())
                result = fn(*args, task_id=task_id, **kwargs)
                self._update(
                    task_id,
                    status="completed",
                    result=json.dumps(result) if result else None,
                    completed_at=utcnow(),
                )
            except Exception as e:
                self._update(
                    task_id,
                    status="failed",
                    error=f"{e}\n{traceback.format_exc()}",
                    completed_at=utcnow(),
                )

        self.executor.submit(wrapper)
        return task_id

    def update_progress(self, task_id: str, message: str):
        """Update progress message for a running task (called from inside the task)."""
        self._update(task_id, progress=message)

    def get_status(self, task_id: str) -> dict | None:
        """Get current status of a task."""
        with SessionLocal() as session:
            task = session.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return None

            d = {
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress or "",
                "result": task.result,
                "error": task.error,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }

            # Parse JSON result if present
            if d.get("result"):
                try:
                    d["result"] = json.loads(d["result"])
                except json.JSONDecodeError:
                    pass

            return d

    def get_recent(self, limit: int = 10) -> list[dict]:
        """Get recent tasks."""
        with SessionLocal() as session:
            tasks = (
                session.query(BackgroundTask)
                .order_by(BackgroundTask.created_at.desc())
                .limit(limit)
                .all()
            )
            results = []
            for task in tasks:
                d = {
                    "id": task.id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "progress": task.progress or "",
                    "result": task.result,
                    "error": task.error,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                }
                results.append(d)
            return results

    def _update(self, task_id: str, **fields):
        """Update task fields in the database."""
        if not fields:
            return
        with SessionLocal() as session:
            task = session.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return
            for key, value in fields.items():
                setattr(task, key, value)
            session.commit()


# Global singleton
task_manager = TaskManager()