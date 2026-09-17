"""
Base class for all job sources.

Every source (JSearch, Adzuna, future ones) implements this interface.
Adding a new source = one new file + register it in the scanner.

Note: DiscoveredJob keeps dates as strings because that's what
the APIs return. Conversion to datetime happens in store.py
when the job enters the database.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import hashlib


@dataclass
class DiscoveredJob:
    """A job listing found by a source, before scoring."""
    source: str           # "jsearch" | "adzuna" | etc.
    title: str
    company: str
    location: str
    remote_type: str      # "remote" | "hybrid" | "onsite" | ""
    salary_range: str
    description: str
    url: str
    posted_at: str = ""           # raw string from API — parsed in store.py
    employment_type: str = ""     # "full_time" | "contract" | "part_time"
    discovered_at: str = ""       # no longer used for DB storage; store.py uses utcnow()

    @property
    def job_id(self) -> str:
        """Stable ID based on URL (or title+company if no URL)."""
        key = self.url if self.url else f"{self.title}|{self.company}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]


class BaseJobSource(ABC):
    """Interface that every job source must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier: 'jsearch', 'adzuna', etc."""
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        location: str = "",
        remote_only: bool = False,
        num_results: int = 10,
    ) -> list[DiscoveredJob]:
        """Search for jobs and return normalized results."""
        ...

    def is_configured(self) -> bool:
        """Check if required API keys are set. Override in subclass."""
        return True