"""
Greenroom scheduler — runs background jobs on a timer.

Jobs:
    1. auto_scan — scans all job sources for all users (every N hours)
    2. auto_prep — preps top matches automatically after scan
    3. morning_brief — compiles and sends daily summary (once per day)
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import settings
from database import (
    SessionLocal, User, Resume, Preference, Job, Application,
    Notification, new_id, utcnow,
)
from state import UserPreferences, ParsedResume, PipelineState, JobDescription, JobScore, CompanyResearch
from store import JobStore
from scanner import scan_jobs
from email_service import send_new_jobs_alert, send_morning_brief

logger = logging.getLogger("greenroom.scheduler")

scheduler = BackgroundScheduler(timezone="UTC")


# ── Job 1: Auto-scan + Auto-prep ──────────────────────────────────────

def auto_scan_all_users():
    """Scan job sources for every user, then auto-prep top matches."""
    logger.info("Auto-scan starting...")
    session = SessionLocal()

    try:
        users = session.query(User).all()

        for user in users:
            pref = session.query(Preference).filter(Preference.user_id == user.id).first()
            resume = session.query(Resume).filter(
                Resume.user_id == user.id, Resume.is_active == True
            ).first()

            if not pref or not resume:
                continue

            logger.info(f"  Scanning for {user.email}...")

            preferences = UserPreferences(
                target_roles=pref.target_roles or [],
                locations=pref.locations or [],
                salary_min=pref.salary_min,
                salary_max=pref.salary_max,
                remote_preference=pref.remote_preference or "any",
                company_size_preference=pref.company_size_preference or [],
                industries=pref.industries or [],
                dealbreakers=pref.dealbreakers or [],
            )
            parsed_resume = ParsedResume(**(resume.parsed_data or {}))

            store = JobStore(user_id=user.id)
            results = scan_jobs(
                preferences=preferences,
                parsed_resume=parsed_resume,
                store=store,
                score_results=True,
                verbose=False,
            )

            new_count = results.get("new_jobs", 0)
            top = results.get("top_matches", [])

            if new_count > 0:
                notif = Notification(
                    id=new_id(),
                    user_id=user.id,
                    type="new_jobs",
                    title=f"🔭 {new_count} new job{'s' if new_count != 1 else ''} found",
                    body=f"Auto-scan found {new_count} new matching jobs.",
                    data={"new_count": new_count, "top_titles": [j.get("title", "") for j in top[:3]]},
                )
                session.add(notif)
                session.commit()

                if user.email_notifications:
                    send_new_jobs_alert(
                        to_email=user.email,
                        user_name=user.name,
                        new_count=new_count,
                        top_jobs=top,
                    )

            # ── Auto-prep top matches ────────────────────────────
            auto_prep_count = settings.AUTO_PREP_TOP_N
            if auto_prep_count > 0 and top:
                _auto_prep_jobs(session, user, resume, top[:auto_prep_count])

            logger.info(f"  {user.email}: {new_count} new jobs")

    except Exception as e:
        logger.error(f"Auto-scan error: {e}", exc_info=True)
    finally:
        session.close()

    logger.info("Auto-scan complete.")


def _auto_prep_jobs(session, user, resume, top_jobs):
    """Auto-prep the top N jobs that haven't been prepped yet."""
    from nodes.resume_parser import parse_resume as _parse
    from nodes.job_scorer import score_job as _score
    from nodes.company_researcher import research_company as _research
    from nodes.resume_tailor import tailor_resume as _tailor
    from nodes.cover_letter import write_cover_letter as _cover
    from nodes.interview_prep import prep_interview as _prep

    parsed_resume = ParsedResume(**(resume.parsed_data or {}))

    for job_dict in top_jobs:
        job_id = job_dict.get("id", "")

        # Skip if already prepped
        existing = session.query(Application).filter(
            Application.user_id == user.id,
            Application.job_id == job_id,
        ).first()
        if existing:
            continue

        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            continue

        logger.info(f"    Auto-prepping: {job.title} @ {job.company}")

        try:
            # Create the application record
            app = Application(
                id=new_id(),
                user_id=user.id,
                job_id=job_id,
                status="processing",
            )
            session.add(app)
            session.commit()

            # Run the pipeline
            state: PipelineState = {
                "resume_raw": resume.raw_text or "",
                "job": JobDescription(
                    raw_text=job.description or "",
                    title=job.title,
                    company=job.company,
                    location=job.location or "",
                    remote_type=job.remote_type or "",
                    salary_range=job.salary_range or "",
                    url=job.url or "",
                    source=job.source,
                ),
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

            state.update(_parse(state))
            state.update(_score(state))
            state.update(_research(state))
            state.update(_tailor(state))
            state.update(_cover(state))
            state.update(_prep(state))

            # Save results
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

            session.commit()

            # Notify user
            notif = Notification(
                id=new_id(),
                user_id=user.id,
                type="app_ready",
                title=f"✨ {job.title} @ {job.company} ready",
                body=f"Your application for {job.title} at {job.company} has been auto-prepped and is ready to review.",
                data={"job_id": job_id, "app_id": app.id},
            )
            session.add(notif)
            session.commit()

            logger.info(f"    ✓ Prepped: {job.title} @ {job.company}")

        except Exception as e:
            logger.error(f"    ✗ Auto-prep failed for {job.title}: {e}")
            # Mark as failed so it doesn't retry
            app_record = session.query(Application).filter(Application.id == app.id).first()
            if app_record:
                app_record.status = "failed"
                session.commit()


# ── Job 2: Morning brief ─────────────────────────────────────────────

def morning_brief_all_users():
    """Compile and send a daily morning brief to all active users."""
    logger.info("Morning brief starting...")
    session = SessionLocal()
    yesterday = utcnow() - timedelta(days=1)

    try:
        users = session.query(User).all()

        for user in users:
            pref = session.query(Preference).filter(Preference.user_id == user.id).first()
            if not pref:
                continue

            new_since = session.query(Job).filter(
                Job.discovered_at >= yesterday,
                Job.user_id == user.id,
            ).count()

            applied_job_ids = [
                a.job_id for a in
                session.query(Application.job_id).filter(Application.user_id == user.id).all()
            ]
            top_query = session.query(Job).filter(
                Job.is_worth_applying == True,
                Job.user_id == user.id,
            )
            if applied_job_ids:
                top_query = top_query.filter(~Job.id.in_(applied_job_ids))
            top_jobs = top_query.order_by(Job.overall_score.desc()).limit(5).all()

            top_dicts = [
                {"title": j.title, "company": j.company, "overall_score": j.overall_score}
                for j in top_jobs
            ]

            app_counts = {}
            for status_val in ["ready", "applied", "interviewing", "offered"]:
                app_counts[status_val] = session.query(Application).filter(
                    Application.user_id == user.id,
                    Application.status == status_val,
                ).count()

            notif = Notification(
                id=new_id(),
                user_id=user.id,
                type="morning_brief",
                title="☀️ Your morning brief",
                body=f"{new_since} new jobs since yesterday. {app_counts.get('ready', 0)} ready to send.",
                data={
                    "new_since_yesterday": new_since,
                    "stats": app_counts,
                    "top_jobs": [j.get("title", "") for j in top_dicts[:3]],
                },
            )
            session.add(notif)
            session.commit()

            if user.email_notifications:
                send_morning_brief(
                    to_email=user.email,
                    user_name=user.name,
                    new_since_yesterday=new_since,
                    top_jobs=top_dicts,
                    stats=app_counts,
                )

            logger.info(f"  Brief sent to {user.email}")

    except Exception as e:
        logger.error(f"Morning brief error: {e}", exc_info=True)
    finally:
        session.close()

    logger.info("Morning brief complete.")


# ── Scheduler setup ───────────────────────────────────────────────────

def start_scheduler():
    """Register jobs and start the scheduler."""
    scheduler.add_job(
        auto_scan_all_users,
        trigger=IntervalTrigger(hours=settings.AUTO_SCAN_HOURS),
        id="auto_scan",
        name="Auto-scan + auto-prep",
        replace_existing=True,
    )

    scheduler.add_job(
        morning_brief_all_users,
        trigger=CronTrigger(hour=settings.MORNING_BRIEF_HOUR, minute=0),
        id="morning_brief",
        name="Daily morning brief",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: auto-scan every {settings.AUTO_SCAN_HOURS}h "
        f"(auto-prep top {settings.AUTO_PREP_TOP_N}), "
        f"morning brief at {settings.MORNING_BRIEF_HOUR}:00 UTC"
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")