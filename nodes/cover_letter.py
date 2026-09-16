"""
Node: write_cover_letter

Generates a personalized cover letter that references:
- Real company info (from research node)
- The candidate's actual matching experience (from score + tailored resume)
- Specific job requirements

This depends on both research_company and tailor_resume completing first.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings
from state import PipelineState
from prompts import WRITE_COVER_LETTER
from utils import extract_text, clean_json

def write_cover_letter(state: PipelineState) -> dict:
    """Write a personalized cover letter for the target job."""
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.5,  # More creative for natural writing voice
        )

        parsed = state["parsed_resume"]
        score = state["score"]
        job = state["job"]
        research = state["company_research"]

        # Build company research summary for the prompt
        research_summary = (
            f"Company: {research.company_name}\n"
            f"Description: {research.description}\n"
            f"Industry: {research.industry}\n"
            f"Recent news: {'; '.join(research.recent_news) if research.recent_news else 'None found'}\n"
            f"Products/Services: {', '.join(research.products_services) if research.products_services else 'Not found'}\n"
            f"Culture: {research.culture_summary or 'Not found'}\n"
            f"Tech stack: {', '.join(research.tech_stack) if research.tech_stack else 'Not found'}\n"
            f"Employee count: {research.employee_count or 'Not found'}\n"
            f"Funding: {research.funding_info or 'Not found'}"
        )

        prompt = WRITE_COVER_LETTER.format(
            candidate_name=parsed.name or "the candidate",
            candidate_summary=parsed.summary or "Experienced professional",
            matching_skills=", ".join(score.matching_skills) or "relevant skills",
            job_title=job.title or "the role",
            job_company=job.company or "the company",
            job_text=job.raw_text,
            company_research=research_summary,
        )

        response = llm.invoke(prompt)

        return {
            "cover_letter": extract_text(response),
            "status": "cover_letter_written",
        }

    except Exception as e:
        return {
            "cover_letter": "",
            "errors": [f"Cover letter writing failed: {e}"],
            "status": "error_cover_letter",
        }
