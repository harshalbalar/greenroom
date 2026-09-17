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
    """Background task: scan job sources + score all results.

    This is what timed out in Phase 3 when done synchronously.
    Now it runs in a background thread and reports progress.
    """
    preferences = UserPreferences(**preferences_dict)
    parsed_resume = ParsedResume(**parsed_resume_dict)

    task_manager.update_progress(task_id, "Searching job sources...")

    store = JobStore()
    results = scan_jobs(
        preferences=preferences,
        parsed_resume=parsed_resume,
        store=store,
        score_results=True,
        verbose=False,
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
    resume_raw: str,
    parsed_resume_dict: dict,
    job_dict: dict,
    task_id: str = "",
) -> dict:
    """Background task: run the full pipeline for one job.

    Runs all 6 nodes sequentially (bypassing the graph gate since
    the user explicitly chose this job). Reports progress per node.
    """
    parsed_resume = ParsedResume(**parsed_resume_dict)

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

    # Run nodes one by one, reporting progress
    task_manager.update_progress(task_id, "Parsing resume...")
    state.update(_parse(state))

    task_manager.update_progress(task_id, "Scoring job match...")
    state.update(_score(state))

    task_manager.update_progress(task_id, "Researching company...")
    state.update(_research(state))

    task_manager.update_progress(task_id, "Tailoring resume...")
    state.update(_tailor(state))

    task_manager.update_progress(task_id, "Writing cover letter...")
    state.update(_cover(state))

    task_manager.update_progress(task_id, "Generating interview prep...")
    state.update(_prep(state))

    # Save results to the applications table
    task_manager.update_progress(task_id, "Saving results...")

    db = SessionLocal()
    try:
        app = Application(
            id=new_id(),
            user_id=user_id,
            job_id=job_id,
            status="ready",
            tailored_resume=state.get("tailored_resume", ""),
            cover_letter=state.get("cover_letter", ""),
            interview_prep=state.get("interview_prep", ""),
        )

        research = state.get("company_research")
        if research and hasattr(research, "model_dump"):
            app.company_research = research.model_dump()

        score = state.get("score")
        if score and hasattr(score, "model_dump"):
            app.score_data = score.model_dump()

        db.add(app)
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
    """Background task: process multiple jobs sequentially.

    Runs the full pipeline for each job, one at a time (to avoid
    hitting Gemini rate limits). Reports progress per job.
    """
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

            # Check if application already exists
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
                    resume_raw=resume_raw,
                    parsed_resume_dict=parsed_resume_dict,
                    job_dict=job_dict,
                    task_id=task_id,
                )
                results.append(result)
            except Exception as e:
                results.append({"job_id": job_id, "error": str(e)})

        return {
            "processed": len(results),
            "results": results,
        }
    finally:
        db.close()
