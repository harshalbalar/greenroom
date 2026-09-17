"""
Task definitions for background processing.

Each task function receives a task_id kwarg so it can report progress.
These run in worker threads, not in the API request thread.
"""

import time
from datetime import datetime, timezone
from worker import task_manager
from state import (
    PipelineState, JobDescription, UserPreferences,
    ParsedResume, JobScore, CompanyResearch,
)
from nodes.resume_parser import parse_resume as _parse
from nodes.job_scorer import score_job as _score
from nodes.company_researcher import research_company as _research
from nodes.resume_tailor import tailor_resume as _tailor
from nodes.cover_letter import write_cover_letter as _cover
from nodes.interview_prep import prep_interview as _prep
from scanner import scan_jobs
from store import JobStore
from database import SessionLocal, Application, Job, Resume, Preference, new_id


def task_scan_and_score(
    user_id: str,
    preferences_dict: dict,
    parsed_resume_dict: dict,
    task_id: str = "",
) -> dict:
    """Background task: scan job sources + score all results."""
    preferences = UserPreferences(**preferences_dict)
    parsed_resume = ParsedResume(**parsed_resume_dict)

    task_manager.update_progress(task_id, "Searching job sources...")

    # Pass user_id so jobs are scoped to this user
    store = JobStore(user_id=user_id)
    results = scan_jobs(
        preferences=preferences,
        parsed_resume=parsed_resume,
        store=store,
        score_results=True,
        verbose=False,
        task_id=task_id,
    )

    return {
        "new_jobs": results.get("new_jobs", 0),
        "duplicates": results.get("duplicates", 0),
        "scored": results.get("scored", 0),
        "worth_applying": results.get("stats", {}).get("worth_applying", 0),
    }


def task_process_application(
    user_id: str,
    job_id: str,
    app_id: str,
    resume_raw: str,
    parsed_resume_dict: dict,
    job_dict: dict,
    task_id: str = "",
) -> dict:
    """Background task: run the full pipeline for one job."""
    db = SessionLocal()
    try:
        existing = db.query(Application).filter(Application.id == app_id).first()
        if existing and existing.status == 'ready':
            return {"application_id": app_id, "status": "already_done"}
    finally:
        db.close()

    parsed_resume = ParsedResume(**parsed_resume_dict)
    company_name = job_dict.get("company", "the company")

    state: PipelineState = {
        "resume_raw": resume_raw,
        "job": JobDescription(**job_dict),
        "preferences": UserPreferences(),
        "parsed_resume": parsed_resume,
        "score": JobScore(),
        "company_research": CompanyResearch(),
        "tailored_resume": "",
        "cover_letter": "",
        "interview_prep": "",
        "errors": [],
        "status": "starting",
    }

    task_manager.update_progress(task_id, f"scout: picking up {company_name} application")
    state.update(_parse(state))

    task_manager.update_progress(task_id, f"analyst: scoring match against your profile")
    state.update(_score(state))

    score = state.get("score")
    score_val = score.overall_score if score else 0
    task_manager.update_progress(task_id, f"remy: researching {company_name}... score {score_val}/100")
    state.update(_research(state))

    task_manager.update_progress(task_id, f"taylor: tailoring resume for {company_name}")
    state.update(_tailor(state))

    task_manager.update_progress(task_id, f"quinn: writing cover letter for {company_name}")
    state.update(_cover(state))

    task_manager.update_progress(task_id, f"quinn: generating interview prep questions")
    state.update(_prep(state))

    task_manager.update_progress(task_id, "Saving results...")

    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            return {"error": "Application not found"}

        app.status = "ready"
        app.tailored_resume = state.get("tailored_resume", "")
        app.cover_letter = state.get("cover_letter", "")
        app.interview_prep = state.get("interview_prep", "")

        research = state.get("company_research")
        if research and hasattr(research, "model_dump"):
            app.company_research = research.model_dump()

        score = state.get("score")
        if score and hasattr(score, "model_dump"):
            app.score_data = score.model_dump()

        db.commit()

        return {
            "application_id": app.id,
            "status": "ready",
            "job_id": job_id,
            "errors": state.get("errors", []),
        }
    finally:
        db.close()


def task_batch_process(
    user_id: str,
    job_ids: list[str],
    resume_raw: str,
    parsed_resume_dict: dict,
    task_id: str = "",
) -> dict:
    """Background task: process multiple jobs sequentially."""
    results = []
    db = SessionLocal()

    try:
        for i, job_id in enumerate(job_ids):
            task_manager.update_progress(
                task_id, f"Processing job {i+1}/{len(job_ids)}..."
            )

            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                results.append({"job_id": job_id, "error": "Job not found"})
                continue

            existing = db.query(Application).filter(
                Application.user_id == user_id,
                Application.job_id == job_id,
            ).first()
            if existing:
                results.append({"job_id": job_id, "error": "Application already exists"})
                continue

            job_dict = {
                "raw_text": job.description or "",
                "title": job.title,
                "company": job.company,
                "location": job.location or "",
                "remote_type": job.remote_type or "",
                "salary_range": job.salary_range or "",
                "url": job.url or "",
                "source": job.source,
            }

            try:
                result = task_process_application(
                    user_id=user_id,
                    job_id=job_id,
                    app_id=new_id(),
                    resume_raw=resume_raw,
                    parsed_resume_dict=parsed_resume_dict,
                    job_dict=job_dict,
                    task_id=task_id,
                )
                results.append(result)
            except Exception as e:
                results.append({"job_id": job_id, "error": str(e)})

        return {"processed": len(results), "results": results}
    finally:
        db.close()