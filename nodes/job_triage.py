"""
Node: triage_job

Fast pre-filter using TypeSafe's Jev decision model.
Classifies jobs as high_fit / maybe / skip in ~150ms, before
the expensive Gemini scoring pipeline fires.

Jev is a "System One" model — it returns typed decisions with
calibrated probabilities, not generated text. This makes it
ideal for binary/choice routing at the start of an agent pipeline.

If TYPESAFE_API_KEY is not set, the node passes everything through
as "maybe" (no filtering, same behavior as before).
"""

import requests
import logging

from config import settings
from state import PipelineState, TriageResult

logger = logging.getLogger(__name__)

JEV_API_URL = "https://api.aimlapi.com/v1/decisions"
JEV_MODEL = "typesafe/jev"


def triage_job(state: PipelineState) -> dict:
    """Ask Jev whether this job is worth scoring with Gemini.

    Sends job title + description + user preferences as state,
    asks a typed Choice question (high_fit / maybe / skip).
    ~150ms, ~$0.04 per million input tokens.

    Uses AI/ML API gateway to access Jev (TypeSafe direct signups
    are currently closed).
    """

    # If no API key, pass everything through (backwards compatible)
    if not settings.TYPESAFE_API_KEY:
        logger.info("Jev triage skipped — no TYPESAFE_API_KEY set")
        return {
            "triage": TriageResult(relevance="maybe", confidence=0.0),
            "status": "triage_skipped",
        }

    try:
        job = state["job"]
        prefs = state["preferences"]
        parsed = state.get("parsed_resume")

        # Build compact state for Jev (stays within 32K context)
        skills_str = ", ".join(parsed.skills[:20]) if parsed else "not parsed yet"
        roles_str = ", ".join(prefs.target_roles) if prefs.target_roles else "any"
        locations_str = ", ".join(prefs.locations) if prefs.locations else "any"

        jev_state = (
            f"=== CANDIDATE ===\n"
            f"Target roles: {roles_str}\n"
            f"Preferred locations: {locations_str}\n"
            f"Remote preference: {prefs.remote_preference}\n"
            f"Key skills: {skills_str}\n"
            f"\n"
            f"=== JOB POSTING ===\n"
            f"Title: {job.title or 'Unknown'}\n"
            f"Company: {job.company or 'Unknown'}\n"
            f"Location: {job.location or 'Unknown'}\n"
            f"Description: {job.raw_text[:3000]}"
        )

        response = requests.post(
            JEV_API_URL,
            headers={
                "Authorization": f"Bearer {settings.TYPESAFE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": JEV_MODEL,
                "state": jev_state,
                "questions": {
                    "relevance": {
                        "type": "choice",
                        "instructions": (
                            "How well does this job match the candidate's "
                            "target roles, skills, and location preferences? "
                            "Consider role title alignment, skill overlap, "
                            "and location/remote fit."
                        ),
                        "criteria": {
                            "high_fit": "Strong match — role title aligns with target roles, most key skills present, location/remote works",
                            "maybe": "Partial match — some overlap in role or skills but not a clear fit, worth a closer look",
                            "skip": "Poor match — wrong field, wrong location with no remote option, or requires skills the candidate clearly lacks",
                        },
                    },
                },
            },
            timeout=5,
        )

        response.raise_for_status()
        data = response.json()

        answer = data.get("answers", {}).get("relevance", {})
        relevance = answer.get("choice", "maybe")
        confidence = answer.get("confidence", 0.0)
        probabilities = answer.get("probabilities", {})

        triage = TriageResult(
            relevance=relevance,
            confidence=confidence,
            probabilities=probabilities,
            skipped=(relevance == "skip" and confidence > 0.7),
        )

        logger.info(
            f"Jev triage: {job.title} @ {job.company} → "
            f"{relevance} (confidence={confidence:.2f}, "
            f"probs={probabilities})"
        )

        return {
            "triage": triage,
            "status": "triaged",
        }

    except requests.Timeout:
        logger.warning("Jev triage timed out — passing through as maybe")
        return {
            "triage": TriageResult(relevance="maybe", confidence=0.0),
            "errors": ["Jev triage timed out — falling back to full scoring"],
            "status": "triage_timeout",
        }
    except Exception as e:
        logger.warning(f"Jev triage failed: {e} — passing through as maybe")
        return {
            "triage": TriageResult(relevance="maybe", confidence=0.0),
            "errors": [f"Jev triage failed: {e} — falling back to full scoring"],
            "status": "triage_error",
        }