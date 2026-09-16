"""
Greenroom — Phase 2 scan runner.

Scans job sources, deduplicates, scores matches, stores in SQLite.

Usage:
    python scan.py                    # Scan + score
    python scan.py --no-score         # Scan only, skip scoring (saves LLM calls)
    python scan.py --stats            # Just show DB stats

Prerequisites:
    1. Phase 1 working (Gemini API key in .env)
    2. At least one job source configured in .env:
       - JSEARCH_API_KEY (from https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
       - ADZUNA_APP_ID + ADZUNA_APP_KEY (from https://developer.adzuna.com)
"""

import sys
from pathlib import Path
from config import settings
from state import UserPreferences, ParsedResume
from store import JobStore
from scanner import scan_jobs
from nodes.resume_parser import parse_resume as parse_resume_node
from state import PipelineState, JobDescription, JobScore, CompanyResearch


def load_and_parse_resume() -> ParsedResume:
    """Load sample resume and parse it (reuses Phase 1 parser)."""
    resume_path = Path(__file__).parent / "test_data" / "sample_resume.txt"
    resume_text = resume_path.read_text()

    print("  Parsing resume...")
    state: PipelineState = {
        "resume_raw": resume_text,
        "job": JobDescription(raw_text=""),
        "preferences": UserPreferences(),
        "parsed_resume": ParsedResume(),
        "score": JobScore(),
        "company_research": CompanyResearch(),
        "tailored_resume": "",
        "cover_letter": "",
        "interview_prep": "",
        "errors": [],
        "status": "",
    }

    result = parse_resume_node(state)
    parsed = result.get("parsed_resume", ParsedResume())
    print(f"  Parsed: {parsed.name} | {len(parsed.skills)} skills | {parsed.years_of_experience} years exp")
    return parsed


def main():
    # Handle flags
    no_score = "--no-score" in sys.argv
    stats_only = "--stats" in sys.argv

    # Stats mode
    if stats_only:
        store = JobStore()
        stats = store.get_stats()
        print(f"\n  Greenroom DB stats:")
        print(f"    Total jobs:      {stats['total']}")
        print(f"    Scored:          {stats['scored']}")
        print(f"    Worth applying:  {stats['worth_applying']}")
        print(f"    Skipped:         {stats['skipped']}")
        print(f"    Unscored:        {stats['unscored']}")

        top = store.get_top_matches(5)
        if top:
            print(f"\n  Top matches:")
            for m in top:
                print(f"    {m['overall_score']}/100 | {m['title']} @ {m['company']}")
        return

    print("\n" + "="*60)
    print("  GREENROOM — Job Scanner (Phase 2)")
    print("="*60)

    # Validate API keys
    missing = settings.validate()
    if missing:
        print(f"\n  Missing API keys: {', '.join(missing)}")
        sys.exit(1)

    available = settings.validate_sources()
    if not available:
        print(f"\n  No job sources configured. Add to .env:")
        print(f"    JSEARCH_API_KEY=your_key    (https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)")
        print(f"    ADZUNA_APP_ID=your_id       (https://developer.adzuna.com)")
        print(f"    ADZUNA_APP_KEY=your_key")
        sys.exit(1)

    print(f"  Sources: {', '.join(available)}")
    print(f"  Score threshold: {settings.JOB_SCORE_THRESHOLD}")
    print(f"  Scoring: {'enabled' if not no_score else 'disabled'}")

    # Parse resume first (needed for scoring)
    parsed_resume = load_and_parse_resume() if not no_score else ParsedResume()

    # Define search preferences
    # TODO: Phase 3 will load these from user's saved profile
    preferences = UserPreferences(
        target_roles=["Senior Software Engineer", "Senior Backend Engineer"],
        locations=["Remote", "San Francisco"],
        salary_min=150000,
        salary_max=300000,
        remote_preference="any",
        company_size_preference=["mid-size", "enterprise"],
    )

    print(f"\n  Preferences:")
    print(f"    Roles: {', '.join(preferences.target_roles)}")
    print(f"    Locations: {', '.join(preferences.locations)}")
    print(f"    Salary: ${preferences.salary_min:,} - ${preferences.salary_max:,}")

    # Run the scan
    print()
    results = scan_jobs(
        preferences=preferences,
        parsed_resume=parsed_resume,
        score_results=not no_score,
        verbose=True,
    )

    print(f"\n{'='*60}")
    print(f"  Done. Run 'python scan.py --stats' to see your DB anytime.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
