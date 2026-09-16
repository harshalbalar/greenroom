"""
Node: parse_resume

Takes raw resume text, sends it to Gemini, gets back structured data.
This runs ONCE per resume and the result is reused by every downstream node.
"""

import json
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings
from state import PipelineState, ParsedResume
from prompts import PARSE_RESUME
from utils import extract_text, clean_json

def parse_resume(state: PipelineState) -> dict:
    """Extract structured resume data from raw text."""
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,  # Low temp for extraction accuracy
        )

        prompt = PARSE_RESUME.format(resume_text=state["resume_raw"])
        response = llm.invoke(prompt)

        # Parse JSON response — strip markdown fences if Gemini adds them
        raw = extract_text(response)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]  # Remove first line (```json)
            raw = raw.rsplit("```", 1)[0]  # Remove last fence

        data = json.loads(raw)
        parsed = ParsedResume(**data)

        return {
            "parsed_resume": parsed,
            "status": "resume_parsed",
        }

    except json.JSONDecodeError as e:
        return {
            "parsed_resume": ParsedResume(),
            "errors": [f"Resume parse failed — invalid JSON from LLM: {e}"],
            "status": "error_parse",
        }
    except Exception as e:
        return {
            "parsed_resume": ParsedResume(),
            "errors": [f"Resume parse failed: {e}"],
            "status": "error_parse",
        }
