"""
Shared utilities for Greenroom nodes.
"""


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
