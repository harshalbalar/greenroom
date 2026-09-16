"""
Job scanner — orchestrates the full discovery flow.

1. Build search queries from user preferences
2. Search all configured sources
3. Deduplicate against the store
4. Score each new job using the Phase 1 scorer
5. Store results

Reuses the Phase 1 job scorer node directly — no duplication.
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


# Registry of all available sources
ALL_SOURCES: list[BaseJobSource] = [
    JSearchSource(),
    AdzunaSource(),
]


def build_search_queries(preferences: UserPreferences) -> list[dict]:
    """Turn user preferences into concrete search queries.

    Returns list of dicts with 'query', 'location', 'remote_only' keys.
    Each gets sent to every configured source.
    """
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

    return queries


def scan_jobs(
    preferences: UserPreferences,
    parsed_resume: ParsedResume,
    store: JobStore | None = None,
    score_results: bool = True,
    verbose: bool = True,
) -> dict:
    """Run a full scan: search → dedup → score → store.

    Args:
        preferences: User's job targeting criteria.
        parsed_resume: Structured resume data (from Phase 1 parser).
        store: JobStore instance. Creates default if None.
        score_results: Whether to score discovered jobs (uses LLM calls).
        verbose: Print progress updates.

    Returns:
        Summary dict with counts and top matches.
    """
    if store is None:
        store = JobStore()

    # Determine which sources are configured
    active_sources = [s for s in ALL_SOURCES if s.is_configured()]
    if not active_sources:
        print("  No job sources configured. Add API keys to .env:")
        print("  - JSearch: JSEARCH_API_KEY (https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)")
        print("  - Adzuna: ADZUNA_APP_ID + ADZUNA_APP_KEY (https://developer.adzuna.com)")
        return {"error": "No sources configured"}

    if verbose:
        print(f"  Active sources: {', '.join(s.name for s in active_sources)}")

    # Build search queries from preferences
    queries = build_search_queries(preferences)
    if verbose:
        print(f"  Search queries: {len(queries)}")
        for q in queries:
            loc = q['location'] or ('remote' if q['remote_only'] else 'any location')
            print(f"    - \"{q['query']}\" in {loc}")

    # Search all sources
    all_discovered: list[DiscoveredJob] = []
    for source in active_sources:
        for q in queries:
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

    if verbose:
        print(f"\n  Total discovered: {len(all_discovered)} jobs")

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
        if verbose:
            print(f"\n  Scoring {len(new_jobs)} jobs...")

        for i, job in enumerate(new_jobs):
            if verbose:
                print(f"  [{i+1}/{len(new_jobs)}] {job.title} @ {job.company}...", end=" ")

            start = time.time()

            # Build a minimal PipelineState for the scorer
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

            store.save_score(job.job_id, score)

            if verbose:
                marker = "+" if score.is_worth_applying else "-"
                print(f"[{marker}] {score.overall_score}/100 ({elapsed:.1f}s)")

            scored_jobs.append({
                "job": job,
                "score": score,
            })

    # Summary
    stats = store.get_stats()
    top_matches = store.get_top_matches(limit=5)

    if verbose:
        print(f"\n  {'='*50}")
        print(f"  Scan complete!")
        print(f"  Total in DB: {stats['total']} | "
              f"Scored: {stats['scored']} | "
              f"Worth applying: {stats['worth_applying']} | "
              f"Skipped: {stats['skipped']}")

        if top_matches:
            print(f"\n  Top matches:")
            for m in top_matches:
                skills = json.loads(m.get("matching_skills", "[]"))
                skills_str = ", ".join(skills[:4])
                print(f"    {m['overall_score']}/100 | {m['title']} @ {m['company']}")
                print(f"           Matching: {skills_str}")

    return {
        "new_jobs": len(new_jobs),
        "duplicates": dupes,
        "scored": len(scored_jobs),
        "stats": stats,
        "top_matches": top_matches,
    }
