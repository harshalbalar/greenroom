"""Resume routes — upload (file or text), parse, list, activate."""

import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db, User, Resume, new_id
from auth_core import get_current_user
from api_schemas import ResumeUploadRequest, ResumeResponse
from nodes.resume_parser import parse_resume as parse_resume_node
from state import PipelineState, JobDescription, UserPreferences, ParsedResume, JobScore, CompanyResearch

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


def _extract_text_from_file(file: UploadFile) -> str:
    """Extract text content from uploaded PDF, DOCX, or TXT file."""
    content = file.file.read()
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
                return "\n\n".join(pages).strip()
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="PDF support not installed. Run: pip install pdfplumber"
            )

    elif filename.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs).strip()
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="DOCX support not installed. Run: pip install python-docx"
            )

    elif filename.endswith(".txt") or filename.endswith(".md"):
        return content.decode("utf-8", errors="ignore").strip()

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {filename}. Upload PDF, DOCX, or TXT."
        )


def _parse_and_store(db: Session, user: User, raw_text: str, filename: str) -> Resume:
    """Parse resume text with Gemini and store both raw + parsed."""
    if len(raw_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Resume text too short (minimum 50 characters)")

    # Deactivate existing active resume
    db.query(Resume).filter(
        Resume.user_id == user.id, Resume.is_active == True
    ).update({"is_active": False})

    # Parse with Gemini
    state: PipelineState = {
        "resume_raw": raw_text,
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
        raw_text=raw_text,
        parsed_data=parsed.model_dump(),
        filename=filename,
        is_active=True,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


# ── Upload via JSON (existing — backward compatible) ──────────────────

@router.post("", response_model=ResumeResponse, status_code=201)
def upload_resume_text(
    req: ResumeUploadRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload resume as raw text (original endpoint)."""
    resume = _parse_and_store(db, user, req.raw_text, req.filename)
    return ResumeResponse(
        id=resume.id, filename=resume.filename, is_active=resume.is_active,
        parsed_data=resume.parsed_data, created_at=resume.created_at,
    )


# ── Upload via file (new — PDF, DOCX, TXT) ───────────────────────────

@router.post("/upload", response_model=ResumeResponse, status_code=201)
def upload_resume_file(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT resume file"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a resume file (PDF, DOCX, or TXT). Extracts text and parses with Gemini."""
    raw_text = _extract_text_from_file(file)

    if not raw_text or len(raw_text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Could not extract enough text from the file. Try pasting the text directly."
        )

    resume = _parse_and_store(db, user, raw_text, file.filename or "resume")
    return ResumeResponse(
        id=resume.id, filename=resume.filename, is_active=resume.is_active,
        parsed_data=resume.parsed_data, created_at=resume.created_at,
    )


# ── List / Active / Activate (unchanged) ─────────────────────────────

@router.get("", response_model=list[ResumeResponse])
def list_resumes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    resume = db.query(Resume).filter(
        Resume.id == resume_id, Resume.user_id == user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    db.query(Resume).filter(Resume.user_id == user.id).update({"is_active": False})
    resume.is_active = True
    db.commit()
    db.refresh(resume)

    return ResumeResponse(
        id=resume.id, filename=resume.filename, is_active=resume.is_active,
        parsed_data=resume.parsed_data or {}, created_at=resume.created_at,
    )
