"""Resume routes — upload, parse, list, activate."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, User, Resume, new_id
from auth_core import get_current_user
from api_schemas import ResumeUploadRequest, ResumeResponse
from nodes.resume_parser import parse_resume as parse_resume_node
from state import PipelineState, JobDescription, UserPreferences, ParsedResume, JobScore, CompanyResearch

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post("", response_model=ResumeResponse, status_code=201)
def upload_resume(
    req: ResumeUploadRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload resume text, parse it with Gemini, and store both raw + parsed."""
    # Deactivate any existing active resume
    db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active == True
    ).update({"is_active": False})

    # Parse resume using Phase 1 parser
    state: PipelineState = {
        "resume_raw": req.raw_text,
        "job": JobDescription(raw_text=""),
        "preferences": UserPreferences(),
        "parsed_resume": ParsedResume(),
        "score": JobScore(),
        "company_research": CompanyResearch(),
        "tailored_resume": "",
        "cover_letter": "",
        "interview_prep": "",
        "errors": [],
        "status": "",
    }
    result = parse_resume_node(state)
    parsed = result.get("parsed_resume", ParsedResume())

    resume = Resume(
        id=new_id(),
        user_id=user.id,
        raw_text=req.raw_text,
        parsed_data=parsed.model_dump(),
        filename=req.filename,
        is_active=True,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return ResumeResponse(
        id=resume.id,
        filename=resume.filename,
        is_active=resume.is_active,
        parsed_data=resume.parsed_data,
        created_at=resume.created_at,
    )


@router.get("", response_model=list[ResumeResponse])
def list_resumes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all resumes for the current user."""
    resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).all()
    return [
        ResumeResponse(
            id=r.id, filename=r.filename, is_active=r.is_active,
            parsed_data=r.parsed_data or {}, created_at=r.created_at,
        )
        for r in resumes
    ]


@router.get("/active", response_model=ResumeResponse)
def get_active_resume(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the user's currently active resume."""
    resume = db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active == True
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No active resume. Upload one first.")

    return ResumeResponse(
        id=resume.id, filename=resume.filename, is_active=resume.is_active,
        parsed_data=resume.parsed_data or {}, created_at=resume.created_at,
    )


@router.patch("/{resume_id}/activate", response_model=ResumeResponse)
def activate_resume(
    resume_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a specific resume as active (deactivates the current one)."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id, Resume.user_id == user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Deactivate all, then activate this one
    db.query(Resume).filter(Resume.user_id == user.id).update({"is_active": False})
    resume.is_active = True
    db.commit()
    db.refresh(resume)

    return ResumeResponse(
        id=resume.id, filename=resume.filename, is_active=resume.is_active,
        parsed_data=resume.parsed_data or {}, created_at=resume.created_at,
    )
