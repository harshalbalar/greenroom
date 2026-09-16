"""
Node: prep_interview

Generates a targeted interview prep guide with:
- Technical questions based on job requirements
- Behavioral questions matched to the candidate's experience
- Company-specific questions showing research depth
- Questions the candidate should ASK
- Key talking points to weave in

This is the last node in the pipeline — it uses everything gathered upstream.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings
from state import PipelineState
from prompts import PREP_INTERVIEW
from utils import extract_text, clean_json

def prep_interview(state: PipelineState) -> dict:
    """Generate targeted interview prep for the role."""
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.4,
        )

        parsed = state["parsed_resume"]
        job = state["job"]
        research = state["company_research"]

        # Build experience highlights for the prompt
        experience_lines = []
        for exp in parsed.experience[:3]:  # Top 3 most recent roles
            highlights = "; ".join(exp.highlights[:3]) if exp.highlights else "N/A"
            experience_lines.append(
                f"- {exp.title} at {exp.company} ({exp.duration}): {highlights}"
            )
        experience_text = "\n".join(experience_lines) if experience_lines else "Not available"

        # Build company context
        company_context = (
            f"Company: {research.company_name}\n"
            f"About: {research.description}\n"
            f"Recent news: {'; '.join(research.recent_news[:3]) if research.recent_news else 'None found'}\n"
            f"Products: {', '.join(research.products_services) if research.products_services else 'Not found'}\n"
            f"Culture: {research.culture_summary or 'Not found'}\n"
            f"Interview insights: {research.interview_insights or 'Not found'}"
        )

        prompt = PREP_INTERVIEW.format(
            candidate_summary=parsed.summary or "Experienced professional",
            skills=", ".join(parsed.skills),
            experience_highlights=experience_text,
            job_title=job.title or "the role",
            job_company=job.company or "the company",
            job_text=job.raw_text,
            company_context=company_context,
        )

        response = llm.invoke(prompt)

        return {
            "interview_prep": extract_text(response),
            "status": "interview_prepped",
        }

    except Exception as e:
        return {
            "interview_prep": "",
            "errors": [f"Interview prep failed: {e}"],
            "status": "error_interview",
        }
