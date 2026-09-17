"""
Shared utilities for Greenroom nodes.
"""

from datetime import datetime, timezone


def extract_text(response) -> str:
    """Extract text from an LLM response, handling both string and list formats.

    Newer langchain-google-genai versions return response.content as a list
    of content parts instead of a plain string. This normalizes both cases.
    """
    content = response.content

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            else:
                parts.append(str(part))
        return "\n".join(parts).strip()

    return str(content).strip()


def clean_json(raw: str) -> str:
    """Strip markdown code fences from LLM JSON output."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]  # Remove first line (```json)
        raw = raw.rsplit("```", 1)[0]  # Remove closing fence
    return raw.strip()


def parse_job_date(date_str: str | None) -> datetime | None:
    """Parse a date string from job APIs into a timezone-aware datetime.

    Job APIs return dates in various formats. This tries common ones and
    returns None if unparseable (don't crash on bad data from external APIs).
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",   # JSearch: 2025-01-15T12:00:00.000Z
        "%Y-%m-%dT%H:%M:%SZ",       # ISO with Z
        "%Y-%m-%dT%H:%M:%S",        # ISO without Z
        "%Y-%m-%d",                  # Adzuna: 2025-01-15
        "%d/%m/%Y",                  # Some EU formats
    ):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None