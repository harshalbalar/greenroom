"""
Job store — SQLAlchemy ORM implementation.

Handles dedup (don't process the same job twice), scoring results,
and status tracking. All queries go through the shared PostgreSQL
database via SQLAlchemy — no separate sqlite3 connection.
"""

from datetime import datetime, timezone

from database import SessionLocal, Job, utcnow
from sources.base import DiscoveredJob
from state import JobScore
from utils import parse_job_date


class JobStore:
    """Job storage using SQLAlchemy ORM.

    Each method opens and closes its own session so the store
    works safely from background threads (scanner, workers).
    """

    def job_exists(self, job_id: str) -> bool:
        """Check if a job is already in the store (for dedup)."""
        with SessionLocal() as session:
            return session.query(Job.id).filter(Job.id == job_id).first() is not None

    def add_job(self, job: DiscoveredJob) -> bool:
        """Add a discovered job. Returns False if duplicate."""
        if self.job_exists(job.job_id):
            return False

        db_job = Job(
            id=job.job_id,
            source=job.source,
            title=job.title,
            company=job.company,
            location=job.location,
            remote_type=job.remote_type,
            salary_range=job.salary_range,
            description=job.description,
            url=job.url,
            posted_at=parse_job_date(job.posted_at),
            employment_type=job.employment_type,
            discovered_at=utcnow(),
            status="discovered",
        )

        with SessionLocal() as session:
            session.add(db_job)
            session.commit()

        return True

    def save_score(self, job_id: str, score: JobScore):
        """Save scoring results for a job."""
        with SessionLocal() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return

            job.overall_score = score.overall_score
            job.skill_match = score.skill_match
            job.experience_match = score.experience_match
            job.location_match = score.location_match
            job.salary_fit = score.salary_fit
            job.culture_fit = score.culture_fit
            job.score_reasoning = score.reasoning
            job.matching_skills = score.matching_skills
            job.missing_skills = score.missing_skills
            job.is_worth_applying = score.is_worth_applying
            job.scored_at = utcnow()
            job.status = "worth_applying" if score.is_worth_applying else "skipped"

            session.commit()

    def get_unscored_jobs(self, limit: int = 20) -> list[dict]:
        """Get jobs that haven't been scored yet."""
        with SessionLocal() as session:
            jobs = (
                session.query(Job)
                .filter(Job.status == "discovered")
                .order_by(Job.discovered_at.desc())
                .limit(limit)
                .all()
            )
            return [self._job_to_dict(j) for j in jobs]

    def get_top_matches(self, limit: int = 10) -> list[dict]:
        """Get highest-scoring jobs worth applying to."""
        with SessionLocal() as session:
            jobs = (
                session.query(Job)
                .filter(Job.is_worth_applying == True)
                .order_by(Job.overall_score.desc())
                .limit(limit)
                .all()
            )
            return [self._job_to_dict(j) for j in jobs]

    def get_stats(self) -> dict:
        """Summary stats for the store."""
        with SessionLocal() as session:
            total = session.query(Job).count()
            scored = session.query(Job).filter(Job.scored_at.isnot(None)).count()
            worth = session.query(Job).filter(Job.is_worth_applying == True).count()
            skipped = session.query(Job).filter(Job.status == "skipped").count()
            unscored = session.query(Job).filter(Job.status == "discovered").count()
            return {
                "total": total,
                "scored": scored,
                "worth_applying": worth,
                "skipped": skipped,
                "unscored": unscored,
            }

    @staticmethod
    def _job_to_dict(job: Job) -> dict:
        """Convert a Job ORM object to a dict (for backward compat with scanner)."""
        return {
            "id": job.id,
            "source": job.source,
            "title": job.title,
            "company": job.company,
            "location": job.location or "",
            "remote_type": job.remote_type or "",
            "salary_range": job.salary_range or "",
            "description": job.description or "",
            "url": job.url or "",
            "posted_at": job.posted_at.isoformat() if job.posted_at else "",
            "employment_type": job.employment_type or "",
            "discovered_at": job.discovered_at.isoformat() if job.discovered_at else "",
            "overall_score": job.overall_score,
            "skill_match": job.skill_match,
            "experience_match": job.experience_match,
            "location_match": job.location_match,
            "salary_fit": job.salary_fit,
            "culture_fit": job.culture_fit,
            "score_reasoning": job.score_reasoning or "",
            "matching_skills": job.matching_skills or [],
            "missing_skills": job.missing_skills or [],
            "is_worth_applying": job.is_worth_applying,
            "scored_at": job.scored_at.isoformat() if job.scored_at else None,
            "status": job.status or "discovered",
        }