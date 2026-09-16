"""
Node: research_company

Two-step process:
1. Tavily search for real company info (news, products, culture, funding)
2. Gemini structures the search results into a clean CompanyResearch object

This is the node that makes cover letters actually good — real company
intel instead of generic "I admire your company's mission" fluff.
"""

import json
from tavily import TavilyClient
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings
from state import PipelineState, CompanyResearch
from prompts import RESEARCH_COMPANY
from utils import extract_text, clean_json

def research_company(state: PipelineState) -> dict:
    """Research company using Tavily search + Gemini structuring."""
    job = state["job"]
    company_name = job.company

    if not company_name:
        return {
            "company_research": CompanyResearch(
                company_name="Unknown",
                description="Company name not found in job description.",
            ),
            "errors": ["No company name found — skipping research"],
            "status": "research_skipped",
        }

    try:
        # Step 1: Search for company info via Tavily
        tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)

        # Run multiple focused searches for better coverage
        queries = [
            f"{company_name} company overview products",
            f"{company_name} recent news funding 2024 2025",
            f"{company_name} engineering culture glassdoor reviews",
        ]

        all_results = []
        for query in queries:
            results = tavily.search(
                query=query,
                max_results=3,
                search_depth="basic",
            )
            for r in results.get("results", []):
                all_results.append(
                    f"Source: {r.get('url', 'N/A')}\n{r.get('content', '')}"
                )

        search_text = "\n\n---\n\n".join(all_results) if all_results else "No search results found."

        # Step 2: Structure results with Gemini
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2,
        )

        prompt = RESEARCH_COMPANY.format(
            company_name=company_name,
            search_results=search_text,
        )

        response = llm.invoke(prompt)

        raw = extract_text(response)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]

        data = json.loads(raw)
        research = CompanyResearch(**data)

        return {
            "company_research": research,
            "status": "company_researched",
        }

    except json.JSONDecodeError as e:
        return {
            "company_research": CompanyResearch(company_name=company_name),
            "errors": [f"Company research failed — invalid JSON: {e}"],
            "status": "error_research",
        }
    except Exception as e:
        return {
            "company_research": CompanyResearch(company_name=company_name),
            "errors": [f"Company research failed: {e}"],
            "status": "error_research",
        }
