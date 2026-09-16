"""
SQLite job store.

Lightweight storage for discovered jobs. Handles dedup (don't process
the same job twice), scoring results, and status tracking.
Migrates to PostgreSQL in Phase 3.
"""

import json
import sqlite3
from datetime import datetime
from config import settings
from sources.base import DiscoveredJob
from state import JobScore


class JobStore:
    def __init__(self, db_path: str = ""):
        self.db_path = db_path or settings.DB_PATH
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT DEFAULT '',
                    remote_type TEXT DEFAULT '',
                    salary_range TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    url TEXT DEFAULT '',
                    posted_at TEXT DEFAULT '',
                    employment_type TEXT DEFAULT '',
                    discovered_at TEXT DEFAULT '',

                    -- Scoring (filled after scoring)
                    overall_score INTEGER,
                    skill_match INTEGER,
                    experience_match INTEGER,
                    location_match INTEGER,
                    salary_fit INTEGER,
                    culture_fit INTEGER,
                    score_reasoning TEXT,
                    matching_skills TEXT,
                    missing_skills TEXT,
                    is_worth_applying BOOLEAN,
                    scored_at TEXT,

                    -- Pipeline status
                    status TEXT DEFAULT 'discovered'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(overall_score)
            """)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def job_exists(self, job_id: str) -> bool:
        """Check if a job is already in the store (for dedup)."""
        with self._conn() as conn:
            row = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return row is not None

    def add_job(self, job: DiscoveredJob) -> bool:
        """Add a discovered job. Returns False if duplicate."""
        if self.job_exists(job.job_id):
            return False

        with self._conn() as conn:
            conn.execute("""
                INSERT INTO jobs (id, source, title, company, location, remote_type,
                    salary_range, description, url, posted_at, employment_type, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.source, job.title, job.company, job.location,
                job.remote_type, job.salary_range, job.description, job.url,
                job.posted_at, job.employment_type, job.discovered_at,
            ))
        return True

    def save_score(self, job_id: str, score: JobScore):
        """Save scoring results for a job."""
        with self._conn() as conn:
            conn.execute("""
                UPDATE jobs SET
                    overall_score = ?, skill_match = ?, experience_match = ?,
                    location_match = ?, salary_fit = ?, culture_fit = ?,
                    score_reasoning = ?, matching_skills = ?, missing_skills = ?,
                    is_worth_applying = ?, scored_at = ?,
                    status = CASE WHEN ? THEN 'worth_applying' ELSE 'skipped' END
                WHERE id = ?
            """, (
                score.overall_score, score.skill_match, score.experience_match,
                score.location_match, score.salary_fit, score.culture_fit,
                score.reasoning,
                json.dumps(score.matching_skills),
                json.dumps(score.missing_skills),
                score.is_worth_applying,
                datetime.now().isoformat(),
                score.is_worth_applying,
                job_id,
            ))

    def get_unscored_jobs(self, limit: int = 20) -> list[dict]:
        """Get jobs that haven't been scored yet."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs WHERE status = 'discovered'
                ORDER BY discovered_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_top_matches(self, limit: int = 10) -> list[dict]:
        """Get highest-scoring jobs worth applying to."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs WHERE is_worth_applying = 1
                ORDER BY overall_score DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Summary stats for the store."""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            scored = conn.execute("SELECT COUNT(*) FROM jobs WHERE scored_at IS NOT NULL").fetchone()[0]
            worth = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_worth_applying = 1").fetchone()[0]
            skipped = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'skipped'").fetchone()[0]
            unscored = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'discovered'").fetchone()[0]
            return {
                "total": total,
                "scored": scored,
                "worth_applying": worth,
                "skipped": skipped,
                "unscored": unscored,
            }
