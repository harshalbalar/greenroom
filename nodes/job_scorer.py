"""
Node: score_job

Scores how well a job matches the candidate's resume and preferences.
Returns scores on 5 dimensions plus a go/no-go decision.
"""

import json
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings
from state import PipelineState, JobScore
from prompts import SCORE_JOB
from utils import extract_text, clean_json

def score_job(state: PipelineState) -> dict:
    """Score job-candidate match across multiple dimensions."""
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2,
        )

        parsed = state["parsed_resume"]
        prefs = state["preferences"]
        job = state["job"]

        # Build salary range string
        salary_parts = []
        if prefs.salary_min:
            salary_parts.append(f"${prefs.salary_min:,}")
        if prefs.salary_max:
            salary_parts.append(f"${prefs.salary_max:,}")
        salary_range = " - ".join(salary_parts) if salary_parts else "Not specified"

        prompt = SCORE_JOB.format(
            skills=", ".join(parsed.skills),
            years_experience=parsed.years_of_experience,
            candidate_location=parsed.location,
            target_roles=", ".join(prefs.target_roles),
            preferred_locations=", ".join(prefs.locations),
            salary_range=salary_range,
            remote_preference=prefs.remote_preference,
            job_title=job.title or "Not specified",
            job_company=job.company or "Not specified",
            job_location=job.location or "Not specified",
            job_remote_type=job.remote_type or "Not specified",
            job_salary=job.salary_range or "Not specified",
            job_text=job.raw_text,
            threshold=settings.JOB_SCORE_THRESHOLD,
        )

        response = llm.invoke(prompt)

        raw = extract_text(response)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]

        data = json.loads(raw)
        score = JobScore(**data)

        return {
            "score": score,
            "status": "job_scored",
        }

    except json.JSONDecodeError as e:
        return {
            "score": JobScore(),
            "errors": [f"Job scoring failed — invalid JSON: {e}"],
            "status": "error_score",
        }
    except Exception as e:
        return {
            "score": JobScore(),
            "errors": [f"Job scoring failed: {e}"],
            "status": "error_score",
        }
