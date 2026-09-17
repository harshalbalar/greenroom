"""
Greenroom configuration.

Reads all settings from environment variables (via .env).
DATABASE_URL controls the database — PostgreSQL in production,
PostgreSQL locally for dev parity.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    JOB_SCORE_THRESHOLD: int = int(os.getenv("JOB_SCORE_THRESHOLD", "60"))

    # Phase 2: Job sources
    JSEARCH_API_KEY: str = os.getenv("JSEARCH_API_KEY", "")
    ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY: str = os.getenv("ADZUNA_APP_KEY", "")

    # Database — PostgreSQL everywhere (local dev + production)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:yourpassword@localhost:5432/greenroom_dev"
    )

    # Render uses legacy "postgres://" prefix — SQLAlchemy needs "postgresql://"
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production-please")

    # Scan settings
    JOBS_PER_SOURCE: int = int(os.getenv("JOBS_PER_SOURCE", "10"))

    # Phase 6C: Email (Resend)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "Greenroom <onboarding@resend.dev>")

    # Phase 6C: Scheduler
    AUTO_SCAN_HOURS: int = int(os.getenv("AUTO_SCAN_HOURS", "6"))
    MORNING_BRIEF_HOUR: int = int(os.getenv("MORNING_BRIEF_HOUR", "8"))  # UTC hour

    def validate(self) -> list[str]:
        """Return list of missing required keys."""
        missing = []
        if not self.GOOGLE_API_KEY:
            missing.append("GOOGLE_API_KEY")
        if not self.TAVILY_API_KEY:
            missing.append("TAVILY_API_KEY")
        return missing

    def validate_sources(self) -> list[str]:
        """Return list of available job sources based on configured keys."""
        available = []
        if self.JSEARCH_API_KEY:
            available.append("jsearch")
        if self.ADZUNA_APP_ID and self.ADZUNA_APP_KEY:
            available.append("adzuna")
        return available


settings = Settings()