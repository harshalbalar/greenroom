"""
AutoApply pipeline state schema.

Design notes:
- Pydantic sub-models for validation and structured LLM output parsing.
- TypedDict for the LangGraph state (LangGraph needs TypedDict, not Pydantic).
- `errors` uses operator.add reducer so every node can append without overwriting.
- `status` tracks which node we're in (useful for SSE streaming in Phase 5).
- Sub-models are intentionally flat — no deep nesting. LLMs produce cleaner
  output when the target schema is simple.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field, field_validator


# ── Resume (parsed by LLM from raw text) ──────────────────────────────

class Experience(BaseModel):
    title: str = ""
    company: str = ""
    duration: str = ""
    highlights: list[str] = Field(default_factory=list)

class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""
    details: str = ""

class Project(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)

class ParsedResume(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    years_of_experience: int = 0
    city: str = ""                                          # NEW
    suggested_roles: list[str] = Field(default_factory=list) # NEW
    nearby_cities: list[str] = Field(default_factory=list)   # NEW


# ── User preferences ──────────────────────────────────────────────────

class UserPreferences(BaseModel):
    target_roles: list[str] = Field(
        default_factory=lambda: ["Software Engineer"]
    )
    locations: list[str] = Field(
        default_factory=lambda: ["Remote"]
    )
    salary_min: int | None = None
    salary_max: int | None = None
    remote_preference: str = "any"  # remote | hybrid | onsite | any
    company_size_preference: list[str] = Field(
        default_factory=list  # startup | mid-size | enterprise
    )
    industries: list[str] = Field(default_factory=list)
    dealbreakers: list[str] = Field(default_factory=list)


# ── Job description (input) ───────────────────────────────────────────

class JobDescription(BaseModel):
    raw_text: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary_range: str = ""
    remote_type: str = ""  # remote | hybrid | onsite | unspecified
    url: str = ""
    source: str = ""  # linkedin | indeed | manual


# ── Job score (output of scorer node) ─────────────────────────────────

class JobScore(BaseModel):
    overall_score: int = 0
    skill_match: int = 0
    experience_match: int = 0
    location_match: int = 0
    salary_fit: int = 0
    culture_fit: int = 0
    reasoning: str = ""
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    is_worth_applying: bool = False

    @field_validator("overall_score", "skill_match", "experience_match", "location_match", "salary_fit", "culture_fit", mode="before")
    @classmethod
    def round_scores(cls, v):
        return round(v) if isinstance(v, float) else v

# ── Company research (output of researcher node) ──────────────────────

class CompanyResearch(BaseModel):
    company_name: str = ""
    description: str = ""
    industry: str = ""
    founded: str = ""
    employee_count: str = ""
    funding_info: str = ""
    recent_news: list[str] = Field(default_factory=list)
    products_services: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    culture_summary: str = ""
    key_people: list[str] = Field(default_factory=list)
    interview_insights: str = ""


# ── Main pipeline state ───────────────────────────────────────────────

class PipelineState(TypedDict):
    # ── Inputs (set once at pipeline start) ──
    resume_raw: str                    # Original resume text
    job: JobDescription                # Job posting
    preferences: UserPreferences       # User's targeting criteria

    # ── Intermediate (built by nodes) ──
    parsed_resume: ParsedResume        # Structured resume from parser
    score: JobScore                    # Match scoring result
    company_research: CompanyResearch  # Research findings

    # ── Final outputs ──
    tailored_resume: str               # Rewritten resume (markdown)
    cover_letter: str                  # Generated cover letter
    interview_prep: str                # Interview questions + talking points

    # ── Pipeline metadata ──
    errors: Annotated[list[str], operator.add]  # Accumulates across nodes
    status: str                        # Current pipeline stage
