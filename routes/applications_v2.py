"""Application routes — create (async), batch, list, update, delete, re-prep, stats.

Phase 4: pipeline runs in background, returns task_id immediately.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, User, Resume, Job, Application, new_id
from auth_core import get_current_user
from api_schemas import (
    ApplicationCreateRequest, ApplicationUpdateRequest,
    ApplicationResponse, ApplicationStatsResponse,
)
from worker import task_manager
from tasks import task_process_application, task_batch_process

router = APIRouter(prefix="/api/applications", tags=["applications"])


class BatchRequest(BaseModel):
    job_ids: list[str]


@router.post("")
def create_application(
    req: ApplicationCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an application for a job. If run_pipeline=true, runs in background."""
    job = db.query(Job).filter(Job.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.query(Application).filter(
        Application.user_id == user.id, Application.job_id == req.job_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Application already exists for this job")

    if not req.run_pipeline:
        app = Application(id=new_id(), user_id=user.id, job_id=req.job_id, status="queued")
        db.add(app)
        db.commit()
        return _to_response(app, job)

    resume = db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active == True
    ).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    parsed_resume_dict = resume.parsed_data if resume.parsed_data else {}
    job_dict = _job_to_dict(job)

    app = Application(id=new_id(), user_id=user.id, job_id=req.job_id, status="processing")
    db.add(app)
    db.commit()

    task_id = task_manager.submit(
        "process_application",
        task_process_application,
        user_id=user.id,
        job_id=req.job_id,
        app_id=app.id,
        resume_raw=resume.raw_text,
        parsed_resume_dict=parsed_resume_dict,
        job_dict=job_dict,
    )

    return {
        "task_id": task_id,
        "status": "processing",
        "job_title": job.title,
        "job_company": job.company,
        "message": "Pipeline started.",
    }


@router.post("/{app_id}/reprep")
def reprep_application(
    app_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-run the pipeline for an existing application. Regenerates all content."""
    app = db.query(Application).filter(
        Application.id == app_id, Application.user_id == user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume = db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active == True
    ).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    # Reset application content
    app.status = "processing"
    app.tailored_resume = ""
    app.cover_letter = ""
    app.interview_prep = ""
    app.company_research = {}
    app.score_data = {}
    app.updated_at = datetime.now(timezone.utc)
    db.commit()

    parsed_resume_dict = resume.parsed_data if resume.parsed_data else {}
    job_dict = _job_to_dict(job)

    task_id = task_manager.submit(
        "process_application",
        task_process_application,
        user_id=user.id,
        job_id=job.id,
        app_id=app.id,
        resume_raw=resume.raw_text,
        parsed_resume_dict=parsed_resume_dict,
        job_dict=job_dict,
    )

    return {
        "task_id": task_id,
        "status": "processing",
        "job_title": job.title,
        "job_company": job.company,
        "message": "Re-prepping with fresh content.",
    }


@router.post("/batch")
def batch_process(
    req: BatchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(req.job_ids) > 10:
        raise HTTPException(status_code=400, detail="Max 10 jobs per batch")

    resume = db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active == True
    ).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    task_id = task_manager.submit(
        "batch_process",
        task_batch_process,
        user_id=user.id,
        job_ids=req.job_ids,
        resume_raw=resume.raw_text,
        parsed_resume_dict=resume.parsed_data if resume.parsed_data else {},
    )

    return {
        "task_id": task_id,
        "status": "processing",
        "job_count": len(req.job_ids),
        "message": f"Batch of {len(req.job_ids)} jobs queued.",
    }


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    status: str = Query(None),
    limit: int = Query(20, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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


def _job_to_dict(job: Job) -> dict:
    return {
        "raw_text": job.description or "",
        "title": job.title,
        "company": job.company,
        "location": job.location or "",
        "remote_type": job.remote_type or "",
        "salary_range": job.salary_range or "",
        "url": job.url or "",
        "source": job.source,
    }


def _to_response(app: Application, job: Job | None) -> ApplicationResponse:
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