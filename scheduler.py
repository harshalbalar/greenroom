"""
Greenroom scheduler — runs background jobs on a timer.

Jobs:
    1. auto_scan — scans all job sources for all users (every N hours)
    2. morning_brief — compiles and sends daily summary (once per day)

Uses APScheduler with the BackgroundScheduler (runs in-process).
On Render's free tier the server can sleep, so jobs only fire when
the app is awake. For guaranteed scheduling, upgrade to the $7/month
always-on tier or use an external cron ping service.
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import settings
from database import SessionLocal, User, Resume, Preference, Job, Application, Notification, new_id, utcnow
from state import UserPreferences, ParsedResume
from store import JobStore
from scanner import scan_jobs
from email_service import send_new_jobs_alert, send_morning_brief

logger = logging.getLogger("greenroom.scheduler")

scheduler = BackgroundScheduler(timezone="UTC")


# ── Job 1: Auto-scan ──────────────────────────────────────────────────

def auto_scan_all_users():
    """Scan job sources for every user who has preferences + resume set up."""
    logger.info("Auto-scan starting...")
    session = SessionLocal()

    try:
        # Find all users with both preferences and an active resume
        users = session.query(User).all()

        for user in users:
            pref = session.query(Preference).filter(Preference.user_id == user.id).first()
            resume = session.query(Resume).filter(
                Resume.user_id == user.id, Resume.is_active == True
            ).first()

            if not pref or not resume:
                continue  # skip users who haven't finished setup

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

            store = JobStore()
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
                # Create in-app notification
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

                # Send email if user opted in
                if user.email_notifications:
                    send_new_jobs_alert(
                        to_email=user.email,
                        user_name=user.name,
                        new_count=new_count,
                        top_jobs=top,
                    )

            logger.info(f"  {user.email}: {new_count} new jobs")

    except Exception as e:
        logger.error(f"Auto-scan error: {e}", exc_info=True)
    finally:
        session.close()

    logger.info("Auto-scan complete.")


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
                continue  # skip users with no preferences

            # Count jobs discovered since yesterday
            new_since = session.query(Job).filter(
                Job.discovered_at >= yesterday
            ).count()

            # Top unprepped matches (worth applying, no application yet)
            applied_job_ids = [
                a.job_id for a in
                session.query(Application.job_id).filter(Application.user_id == user.id).all()
            ]
            top_query = session.query(Job).filter(
                Job.is_worth_applying == True,
            )
            if applied_job_ids:
                top_query = top_query.filter(~Job.id.in_(applied_job_ids))
            top_jobs = top_query.order_by(Job.overall_score.desc()).limit(5).all()

            top_dicts = [
                {"title": j.title, "company": j.company, "overall_score": j.overall_score}
                for j in top_jobs
            ]

            # Application stats
            app_counts = {}
            for status_val in ["ready", "applied", "interviewing", "offered"]:
                app_counts[status_val] = session.query(Application).filter(
                    Application.user_id == user.id,
                    Application.status == status_val,
                ).count()

            # Create in-app notification
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

            # Send email if opted in
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
    """Register jobs and start the scheduler. Called from server.py lifespan."""
    # Auto-scan every N hours
    scheduler.add_job(
        auto_scan_all_users,
        trigger=IntervalTrigger(hours=settings.AUTO_SCAN_HOURS),
        id="auto_scan",
        name="Auto-scan job sources",
        replace_existing=True,
    )

    # Morning brief at configured hour (UTC)
    scheduler.add_job(
        morning_brief_all_users,
        trigger=CronTrigger(hour=settings.MORNING_BRIEF_HOUR, minute=0),
        id="morning_brief",
        name="Daily morning brief",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: auto-scan every {settings.AUTO_SCAN_HOURS}h, "
        f"morning brief at {settings.MORNING_BRIEF_HOUR}:00 UTC"
    )


def stop_scheduler():
    """Shut down cleanly. Called from server.py lifespan."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
