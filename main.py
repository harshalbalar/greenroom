"""
Greenroom — Phase 1 test runner.

Usage:
    cd greenroom
    cp .env.example .env   # Fill in your API keys
    pip install -r requirements.txt
    python main.py
"""

import sys
import time
from pathlib import Path
from config import settings
from state import PipelineState, JobDescription, UserPreferences, ParsedResume, JobScore, CompanyResearch
from graph import pipeline


def load_test_data() -> tuple[str, str]:
    """Load sample resume and job description from test_data/."""
    resume_path = Path(__file__).parent / "test_data" / "sample_resume.txt"
    job_path = Path(__file__).parent / "test_data" / "sample_job.txt"

    resume_text = resume_path.read_text()
    job_text = job_path.read_text()

    return resume_text, job_text


def print_section(title: str, content: str, max_lines: int = 0) -> None:
    """Print a formatted section."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    if max_lines and content:
        lines = content.split("\n")
        print("\n".join(lines[:max_lines]))
        if len(lines) > max_lines:
            print(f"\n  ... ({len(lines) - max_lines} more lines)")
    else:
        print(content or "(empty)")


def main():
    # Validate API keys
    missing = settings.validate()
    if missing:
        print(f"\n  Missing API keys: {', '.join(missing)}")
        print(f"  Copy .env.example to .env and fill in your keys.")
        print(f"  - Gemini: https://aistudio.google.com/apikey")
        print(f"  - Tavily: https://tavily.com")
        sys.exit(1)

    # Load test data
    resume_text, job_text = load_test_data()

    # Build initial state
    initial_state: PipelineState = {
        "resume_raw": resume_text,
        "job": JobDescription(
            raw_text=job_text,
            title="Senior Backend Engineer",
            company="Stripe",
            location="San Francisco, CA",
            remote_type="hybrid",
            salary_range="$180,000 - $250,000",
            url="https://stripe.com/jobs/example",
            source="manual",
        ),
        "preferences": UserPreferences(
            target_roles=["Senior Software Engineer", "Senior Backend Engineer", "Staff Engineer"],
            locations=["San Francisco", "Remote"],
            salary_min=170000,
            salary_max=280000,
            remote_preference="hybrid",
            company_size_preference=["mid-size", "enterprise"],
        ),
        # Intermediate — will be filled by nodes
        "parsed_resume": ParsedResume(),
        "score": JobScore(),
        "company_research": CompanyResearch(),
        # Outputs — will be filled by nodes
        "tailored_resume": "",
        "cover_letter": "",
        "interview_prep": "",
        # Metadata
        "errors": [],
        "status": "starting",
    }

    print("\n" + "="*70)
    print("  GREENROOM — Phase 1 Pipeline Test")
    print("  Your applications, prepped and ready.")
    print("="*70)
    print(f"\n  Resume: Sarah Chen (sample)")
    print(f"  Job:    Senior Backend Engineer @ Stripe")
    print(f"  Model:  {settings.GEMINI_MODEL}")
    print(f"  Score threshold: {settings.JOB_SCORE_THRESHOLD}")

    # Run the pipeline
    start_time = time.time()

    print("\n  Running pipeline...\n")

    # Stream node execution for visibility
    for event in pipeline.stream(initial_state, stream_mode="updates"):
        for node_name, updates in event.items():
            status = updates.get("status", "")
            elapsed = time.time() - start_time
            print(f"  [{elapsed:5.1f}s] {node_name}: {status}")

            # Show score details inline
            if node_name == "score_job" and "score" in updates:
                s = updates["score"]
                print(f"           Overall: {s.overall_score}/100 | "
                      f"Skills: {s.skill_match} | Exp: {s.experience_match} | "
                      f"Location: {s.location_match} | Salary: {s.salary_fit}")
                print(f"           Worth applying: {s.is_worth_applying}")
                if not s.is_worth_applying:
                    print(f"\n  Pipeline stopped — score below threshold.")

    total_time = time.time() - start_time

    # Get final state
    final_state = pipeline.invoke(initial_state)

    # Print results
    print(f"\n  Total pipeline time: {total_time:.1f}s")

    if final_state.get("errors"):
        print(f"\n  Errors encountered:")
        for err in final_state["errors"]:
            print(f"    - {err}")

    # Score
    score = final_state.get("score")
    if score and score.overall_score > 0:
        print_section("JOB MATCH SCORE", (
            f"Overall: {score.overall_score}/100\n"
            f"Skill match: {score.skill_match}/100\n"
            f"Experience match: {score.experience_match}/100\n"
            f"Location match: {score.location_match}/100\n"
            f"Salary fit: {score.salary_fit}/100\n"
            f"Culture fit: {score.culture_fit}/100\n\n"
            f"Matching skills: {', '.join(score.matching_skills)}\n"
            f"Missing skills: {', '.join(score.missing_skills)}\n\n"
            f"Reasoning: {score.reasoning}"
        ))

    # Only show full outputs if the pipeline continued past scoring
    if score and score.is_worth_applying:
        # Company research
        research = final_state.get("company_research")
        if research and research.description:
            print_section("COMPANY RESEARCH", (
                f"Company: {research.company_name}\n"
                f"Industry: {research.industry}\n"
                f"Description: {research.description}\n"
                f"Employees: {research.employee_count}\n"
                f"Funding: {research.funding_info}\n"
                f"Recent news: {'; '.join(research.recent_news[:3])}\n"
                f"Products: {', '.join(research.products_services[:5])}\n"
                f"Culture: {research.culture_summary}"
            ))

        # Tailored resume
        if final_state.get("tailored_resume"):
            print_section("TAILORED RESUME", final_state["tailored_resume"], max_lines=30)

        # Cover letter
        if final_state.get("cover_letter"):
            print_section("COVER LETTER", final_state["cover_letter"])

        # Interview prep
        if final_state.get("interview_prep"):
            print_section("INTERVIEW PREP", final_state["interview_prep"], max_lines=40)

    print(f"\n{'='*70}")
    print(f"  Pipeline complete. Total time: {total_time:.1f}s")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
