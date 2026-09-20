"""
Greenroom database — SQLAlchemy models + session management.

PostgreSQL in production (Render), PostgreSQL locally for dev parity.
Migrations handled by Alembic — never call create_all() in production.

Models: User, Resume, Preference, Job, Application, BackgroundTask, Notification
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean, Text, DateTime, Float,
    ForeignKey, Index, JSON, LargeBinary,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config import settings


# ── Engine + Session ──────────────────────────────────────────────────

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session, auto-closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def new_id() -> str:
    return uuid.uuid4().hex[:16]


# ── Utility ───────────────────────────────────────────────────────────

def utcnow() -> datetime:
    """Consistent UTC timestamps everywhere."""
    return datetime.now(timezone.utc)


# ── Models ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_id)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    email_notifications = Column(Boolean, default=True)

    resumes = relationship("Resume", back_populates="user")
    preference = relationship("Preference", back_populates="user", uselist=False)
    applications = relationship("Application", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    raw_text = Column(Text, default="")
    parsed_data = Column(JSON, default=dict)
    filename = Column(String, default="")
    is_active = Column(Boolean, default=True)
    original_file = Column(LargeBinary, nullable=True)  # raw DOCX bytes for "My Template"
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="resumes")


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    target_roles = Column(JSON, default=list)
    locations = Column(JSON, default=list)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    remote_preference = Column(String, default="any")
    company_size_preference = Column(JSON, default=list)
    industries = Column(JSON, default=list)
    dealbreakers = Column(JSON, default=list)
    updated_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="preference")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    source = Column(String, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, default="")
    remote_type = Column(String, default="")
    salary_range = Column(String, default="")
    description = Column(Text, default="")
    url = Column(String, default="")
    employment_type = Column(String, default="")

    posted_at = Column(DateTime(timezone=True), nullable=True)
    discovered_at = Column(DateTime(timezone=True), default=utcnow)

    overall_score = Column(Integer, nullable=True)
    skill_match = Column(Integer, nullable=True)
    experience_match = Column(Integer, nullable=True)
    location_match = Column(Integer, nullable=True)
    salary_fit = Column(Integer, nullable=True)
    culture_fit = Column(Integer, nullable=True)
    score_reasoning = Column(Text, nullable=True)
    matching_skills = Column(JSON, nullable=True)
    missing_skills = Column(JSON, nullable=True)
    is_worth_applying = Column(Boolean, nullable=True)
    scored_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(String, default="discovered")

    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_score", "overall_score"),
        Index("idx_jobs_discovered", "discovered_at"),
        Index("idx_jobs_user", "user_id"),
    )


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default="queued")

    tailored_resume = Column(Text, default="")
    cover_letter = Column(Text, default="")
    interview_prep = Column(Text, default="")
    company_research = Column(JSON, default=dict)
    score_data = Column(JSON, default=dict)

    applied_at = Column(DateTime(timezone=True), nullable=True)
    followed_up_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="applications")
    job = relationship("Job")


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id = Column(String, primary_key=True)
    task_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    progress = Column(Text, default="")
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, default="")
    data = Column(JSON, default=dict)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("idx_notif_user_read", "user_id", "is_read"),
    )


# ── Table creation (DEV ONLY) ─────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)