"""Application routes — create, list, update, delete, stats.

Creating an application triggers the full Phase 1 pipeline:
research → tailor resume → cover letter → interview prep.
Results are stored and presented for one-click approval.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from routes.auth import get_current_user
from database import get_db, User, Resume, Job, Application, new_id
from auth_core import get_current_user
from nodes.resume_parser import parse_resume as _parse
from nodes.company_researcher import research_company as _research
from nodes.resume_tailor import tailor_resume as _tailor
from nodes.cover_letter import write_cover_letter as _cover
from nodes.interview_prep import prep_interview as _prep
from nodes.job_scorer import score_job as _score
from api_schemas import (
    ApplicationCreateRequest, ApplicationUpdateRequest,
    ApplicationResponse, ApplicationStatsResponse,
)
from state import (
    PipelineState, JobDescription, UserPreferences,
    ParsedResume, JobScore, CompanyResearch, TriageResult,
)
from graph import pipeline as greenroom_pipeline

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.post("", response_model=ApplicationResponse, status_code=201)
def create_application(
    req: ApplicationCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an application for a job. Optionally runs the full pipeline."""
    # Validate job exists
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check for duplicate application
    existing = db.query(Application).filter(
        Application.user_id == user.id, Application.job_id == req.job_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Application already exists for this job")

    # Get active resume
    resume = db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active == True
    ).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    app = Application(
        id=new_id(),
        user_id=user.id,
        job_id=req.job_id,
        status="queued",
    )

    if req.run_pipeline:
        # Run the full Phase 1 pipeline
        parsed_resume = ParsedResume(**resume.parsed_data) if resume.parsed_data else ParsedResume()

        initial_state: PipelineState = {
            "resume_raw": resume.raw_text,
            "job": JobDescription(
                raw_text=job.description or "",
                title=job.title,
                company=job.company,
                location=job.location or "",
                remote_type=job.remote_type or "",
                salary_range=job.salary_range or "",
                url=job.url or "",
                source=job.source,
            ),
            "preferences": UserPreferences(),
            "parsed_resume": parsed_resume,
            "triage": TriageResult(),
            "score": JobScore(),
            "company_research": CompanyResearch(),
            "tailored_resume": "",
            "cover_letter": "",
            "interview_prep": "",
            "errors": [],
            "status": "starting",
        }



        state = dict(initial_state)
        state.update(_parse(state))
        state.update(_score(state))
        state.update(_research(state))
        state.update(_tailor(state))
        state.update(_cover(state))
        state.update(_prep(state))
        final_state = state

        app.tailored_resume = final_state.get("tailored_resume", "")
        app.cover_letter = final_state.get("cover_letter", "")
        app.interview_prep = final_state.get("interview_prep", "")

        research = final_state.get("company_research")
        if research:
            app.company_research = research.model_dump()

        score = final_state.get("score")
        if score:
            app.score_data = score.model_dump()

        app.status = "ready"  # Pipeline completed — ready for user review

    db.add(app)
    db.commit()
    db.refresh(app)

    return _to_response(app, job)


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    status: str = Query(None),
    limit: int = Query(20, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the user's applications, optionally filtered by status."""
    query = db.query(Application).filter(Application.user_id == user.id)
    if status:
        query = query.filter(Application.status == status)

    apps = query.order_by(Application.created_at.desc()).limit(limit).all()

    results = []
    for app in apps:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        results.append(_to_response(app, job))
    return results


@router.get("/stats", response_model=ApplicationStatsResponse)
def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get application pipeline stats for the current user."""
    apps = db.query(Application).filter(Application.user_id == user.id).all()
    stats = ApplicationStatsResponse(total=len(apps))
    for app in apps:
        if app.status == "queued": stats.queued += 1
        elif app.status == "ready": stats.ready += 1
        elif app.status == "applied": stats.applied += 1
        elif app.status == "interviewing": stats.interviewing += 1
        elif app.status == "offered": stats.offered += 1
        elif app.status == "rejected": stats.rejected += 1
        elif app.status == "ghosted": stats.ghosted += 1
    return stats


@router.patch("/{app_id}", response_model=ApplicationResponse)
def update_application(
    app_id: str,
    req: ApplicationUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an application's status or notes."""
    app = db.query(Application).filter(
        Application.id == app_id, Application.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if req.status is not None:
        valid = {"queued", "ready", "applied", "interviewing", "offered", "rejected", "ghosted"}
        if req.status not in valid:
            raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(valid)}")
        app.status = req.status
    if req.notes is not None:
        app.notes = req.notes
    if req.applied_at is not None:
        app.applied_at = req.applied_at

    app.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(app)

    job = db.query(Job).filter(Job.id == app.job_id).first()
    return _to_response(app, job)


@router.delete("/{app_id}", status_code=204)
def delete_application(
    app_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an application."""
    app = db.query(Application).filter(
        Application.id == app_id, Application.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(app)
    db.commit()


def _to_response(app: Application, job: Job | None) -> ApplicationResponse:
    """Convert DB application + job to API response."""
    return ApplicationResponse(
        id=app.id,
        job_id=app.job_id,
        status=app.status or "queued",
        tailored_resume=app.tailored_resume or "",
        cover_letter=app.cover_letter or "",
        interview_prep=app.interview_prep or "",
        company_research=app.company_research or {},
        score_data=app.score_data or {},
        applied_at=app.applied_at,
        followed_up_at=app.followed_up_at,
        notes=app.notes or "",
        created_at=app.created_at,
        updated_at=app.updated_at,
        job_title=job.title if job else "",
        job_company=job.company if job else "",
        job_url=job.url if job else "",
    )