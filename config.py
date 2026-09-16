import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    JOB_SCORE_THRESHOLD: int = int(os.getenv("JOB_SCORE_THRESHOLD", "60"))

    # Phase 2: Job sources
    JSEARCH_API_KEY: str = os.getenv("JSEARCH_API_KEY", "")
    ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY: str = os.getenv("ADZUNA_APP_KEY", "")

    # Database
    DB_PATH: str = os.getenv("DB_PATH", "greenroom.db")

    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production-please")

    # Scan settings
    JOBS_PER_SOURCE: int = int(os.getenv("JOBS_PER_SOURCE", "10"))

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
