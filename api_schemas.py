from datetime import datetime
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field('', max_length=100)

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime | None = None

class ResumeUploadRequest(BaseModel):
    raw_text: str = Field(..., min_length=50)
    filename: str = Field('resume.txt', max_length=255)

class ResumeResponse(BaseModel):
    id: str
    filename: str
    is_active: bool
    parsed_data: dict = {}
    has_original_file: bool = False  # True when DOCX was uploaded → "My Template" available
    created_at: datetime | None = None

class PreferenceRequest(BaseModel):
    target_roles: list[str] = Field(default_factory=lambda: ['Software Engineer'])
    locations: list[str] = Field(default_factory=lambda: ['Remote'])
    salary_min: int | None = None
    salary_max: int | None = None
    remote_preference: str = 'any'
    company_size_preference: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    dealbreakers: list[str] = Field(default_factory=list)

class PreferenceResponse(PreferenceRequest):
    id: str
    updated_at: datetime | None = None

class JobResponse(BaseModel):
    id: str
    source: str
    title: str
    company: str
    location: str
    remote_type: str
    salary_range: str
    url: str
    overall_score: int | None = None
    skill_match: int | None = None
    experience_match: int | None = None
    matching_skills: list[str] = []
    missing_skills: list[str] = []
    is_worth_applying: bool | None = None
    score_reasoning: str = ''
    status: str = 'discovered'

class ScanRequest(BaseModel):
    score_results: bool = True

class ScanResponse(BaseModel):
    new_jobs: int
    duplicates: int
    scored: int
    worth_applying: int

class ApplicationCreateRequest(BaseModel):
    job_id: str
    run_pipeline: bool = True

class ApplicationUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = None
    applied_at: datetime | None = None

class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    status: str
    tailored_resume: str = ''
    cover_letter: str = ''
    interview_prep: str = ''
    company_research: dict = {}
    score_data: dict = {}
    applied_at: datetime | None = None
    followed_up_at: datetime | None = None
    notes: str = ''
    created_at: datetime | None = None
    updated_at: datetime | None = None
    job_title: str = ''
    job_company: str = ''
    job_url: str = ''

class ApplicationStatsResponse(BaseModel):
    total: int = 0
    queued: int = 0
    ready: int = 0
    applied: int = 0
    interviewing: int = 0
    offered: int = 0
    rejected: int = 0
    ghosted: int = 0