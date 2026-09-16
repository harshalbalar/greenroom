"""
Node: tailor_resume

Rewrites the resume to emphasize relevant experience for the target job.
Does NOT fabricate — only reorders, re-emphasizes, and adjusts keywords.

This is where the product earns its keep: a well-tailored resume takes
a human 20+ minutes per application. This does it in ~15 seconds.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings
from state import PipelineState
from prompts import TAILOR_RESUME
from utils import extract_text, clean_json

def tailor_resume(state: PipelineState) -> dict:
    """Tailor resume for a specific job posting."""
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3,  # Slightly creative but still factual
        )

        parsed = state["parsed_resume"]
        score = state["score"]
        job = state["job"]

        prompt = TAILOR_RESUME.format(
            resume_text=state["resume_raw"],
            skills=", ".join(parsed.skills),
            matching_skills=", ".join(score.matching_skills) or "None identified",
            missing_skills=", ".join(score.missing_skills) or "None identified",
            job_title=job.title or "the role",
            job_company=job.company or "the company",
            job_text=job.raw_text,
        )

        response = llm.invoke(prompt)

        return {
            "tailored_resume": extract_text(response),
            "status": "resume_tailored",
        }

    except Exception as e:
        return {
            "tailored_resume": "",
            "errors": [f"Resume tailoring failed: {e}"],
            "status": "error_tailor",
        }
