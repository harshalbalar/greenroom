"""
Job scanner — orchestrates the full discovery flow.

1. Build search queries from user preferences
2. Search all configured sources
3. Deduplicate against the store
4. Score each new job using the Phase 1 scorer
5. Store results
"""

import json
import time
from config import settings
from state import (
    PipelineState, JobDescription, UserPreferences,
    ParsedResume, JobScore, CompanyResearch,
)
from nodes.job_scorer import score_job
from sources.base import BaseJobSource, DiscoveredJob
from sources.jsearch import JSearchSource
from sources.adzuna import AdzunaSource
from store import JobStore
from worker import task_manager


ALL_SOURCES: list[BaseJobSource] = [
    JSearchSource(),
    AdzunaSource(),
]


def build_search_queries(preferences: UserPreferences) -> list[dict]:
    """Turn user preferences into concrete search queries."""
    queries = []
    locations = preferences.locations if preferences.locations else [""]
    roles = preferences.target_roles if preferences.target_roles else ["Software Engineer"]

    for role in roles:
        for location in locations:
            is_remote = location.lower() in ("remote", "anywhere", "")
            queries.append({
                "query": role,
                "location": "" if is_remote else location,
                "remote_only": is_remote and preferences.remote_preference == "remote",
            })

    # Cap at 10 queries to avoid burning API limits
    if len(queries) > 10:
        queries = queries[:10]

    return queries


def scan_jobs(
    preferences: UserPreferences,
    parsed_resume: ParsedResume,
    store: JobStore | None = None,
    score_results: bool = True,
    verbose: bool = True,
    task_id: str = "",
) -> dict:
    """Run a full scan: search → dedup → score → store."""
    if store is None:
        store = JobStore()

    active_sources = [s for s in ALL_SOURCES if s.is_configured()]
    if not active_sources:
        if verbose:
            print("  No job sources configured.")
        return {"error": "No sources configured"}

    if verbose:
        print(f"  Active sources: {', '.join(s.name for s in active_sources)}")

    queries = build_search_queries(preferences)

    # Search all sources
    all_discovered: list[DiscoveredJob] = []
    for source in active_sources:
        for q in queries:
            if task_id:
                task_manager.update_progress(task_id, f"scout: searching {source.name}...")
            if verbose:
                print(f"\n  [{source.name}] Searching: {q['query']}", end="")
                if q["location"]:
                    print(f" in {q['location']}", end="")
                print("...")

            results = source.search(
                query=q["query"],
                location=q["location"],
                remote_only=q["remote_only"],
                num_results=settings.JOBS_PER_SOURCE,
            )

            if verbose:
                print(f"  [{source.name}] Found {len(results)} jobs")
            all_discovered.extend(results)

    if task_id:
        task_manager.update_progress(task_id, f"scout: found {len(all_discovered)} jobs, deduplicating...")

    # Deduplicate against store
    new_jobs: list[DiscoveredJob] = []
    dupes = 0
    for job in all_discovered:
        if store.add_job(job):
            new_jobs.append(job)
        else:
            dupes += 1

    if verbose:
        print(f"  New jobs: {len(new_jobs)} (skipped {dupes} duplicates)")

    # Score new jobs
    scored_jobs = []
    if score_results and new_jobs:
        if task_id:
            task_manager.update_progress(task_id, f"analyst: scoring {len(new_jobs)} jobs...")

        for i, job in enumerate(new_jobs):
            job_id = store.get_job_id(job)

            if task_id:
                task_manager.update_progress(
                    task_id, f"analyst: scoring {job.title} @ {job.company} [{i+1}/{len(new_jobs)}]"
                )

            if verbose:
                print(f"  [{i+1}/{len(new_jobs)}] {job.title} @ {job.company}...", end=" ")

            start = time.time()

            score_state: PipelineState = {
                "resume_raw": "",
                "job": JobDescription(
                    raw_text=job.description,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    remote_type=job.remote_type,
                    salary_range=job.salary_range,
                    url=job.url,
                    source=job.source,
                ),
                "preferences": preferences,
                "parsed_resume": parsed_resume,
                "score": JobScore(),
                "company_research": CompanyResearch(),
                "tailored_resume": "",
                "cover_letter": "",
                "interview_prep": "",
                "errors": [],
                "status": "",
            }

            result = score_job(score_state)
            score = result.get("score", JobScore())
            elapsed = time.time() - start

            store.save_score(job_id, score)

            if verbose:
                marker = "+" if score.is_worth_applying else "-"
                print(f"[{marker}] {score.overall_score}/100 ({elapsed:.1f}s)")

            scored_jobs.append({"job": job, "score": score})

    stats = store.get_stats()
    top_matches = store.get_top_matches(limit=5)

    if verbose:
        print(f"\n  Scan complete!")
        print(f"  Total: {stats['total']} | Worth: {stats['worth_applying']} | Skipped: {stats['skipped']}")

    return {
        "new_jobs": len(new_jobs),
        "duplicates": dupes,
        "scored": len(scored_jobs),
        "stats": stats,
        "top_matches": top_matches,
    }