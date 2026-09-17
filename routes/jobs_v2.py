"""Jobs routes — scan for jobs, list results, get details.

Phase 4: scan runs in background, returns task_id immediately.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db, User, Resume, Preference, Job
from auth_core import get_current_user
from api_schemas import JobResponse, ScanRequest, ScanResponse
from state import UserPreferences, ParsedResume
from worker import task_manager
from tasks import task_scan_and_score

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _prefs_from_db(pref: Preference) -> UserPreferences:
    return UserPreferences(
        target_roles=pref.target_roles or [],
        locations=pref.locations or [],
        salary_min=pref.salary_min,
        salary_max=pref.salary_max,
        remote_preference=pref.remote_preference or "any",
        company_size_preference=pref.company_size_preference or [],
        industries=pref.industries or [],
        dealbreakers=pref.dealbreakers or [],
    )


@router.post("/scan")
def trigger_scan(
    req: ScanRequest = ScanRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scan all job sources. Runs in background, returns task_id."""
    pref = db.query(Preference).filter(Preference.user_id == user.id).first()
    if not pref:
        raise HTTPException(status_code=400, detail="Set your preferences first")

    resume = db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active == True
    ).first()
    if not resume and req.score_results:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    preferences = _prefs_from_db(pref)
    parsed_resume = ParsedResume(**(resume.parsed_data if resume else {}))

    task_id = task_manager.submit(
        "scan_and_score",
        task_scan_and_score,
        user_id=user.id,
        preferences_dict=preferences.model_dump(),
        parsed_resume_dict=parsed_resume.model_dump(),
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Scan started. Poll /api/events/{task_id}/status for progress.",
    }


@router.get("", response_model=list[JobResponse])
def list_jobs(
    status: str = Query(None),
    worth_only: bool = Query(False),
    limit: int = Query(20, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List discovered jobs for the current user only."""
    query = db.query(Job).filter(Job.user_id == user.id)

    if worth_only:
        query = query.filter(Job.is_worth_applying == True)
    elif status:
        query = query.filter(Job.status == status)

    jobs = query.order_by(Job.overall_score.desc().nullslast()).limit(limit).all()

    return [
        JobResponse(
            id=j.id, source=j.source, title=j.title, company=j.company,
            location=j.location or "", remote_type=j.remote_type or "",
            salary_range=j.salary_range or "", url=j.url or "",
            overall_score=j.overall_score, skill_match=j.skill_match,
            experience_match=j.experience_match,
            matching_skills=j.matching_skills or [],
            missing_skills=j.missing_skills or [],
            is_worth_applying=j.is_worth_applying,
            score_reasoning=j.score_reasoning or "",
            status=j.status or "discovered",
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single job's full details (must belong to current user)."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id, source=job.source, title=job.title, company=job.company,
        location=job.location or "", remote_type=job.remote_type or "",
        salary_range=job.salary_range or "", url=job.url or "",
        overall_score=job.overall_score, skill_match=job.skill_match,
        experience_match=job.experience_match,
        matching_skills=job.matching_skills or [],
        missing_skills=job.missing_skills or [],
        is_worth_applying=job.is_worth_applying,
        score_reasoning=job.score_reasoning or "",
        status=job.status or "discovered",
    )