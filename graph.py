"""
Greenroom LangGraph pipeline.

Flow:
  parse_resume → triage_job (Jev) → [should_triage?]
    SKIP → END (job irrelevant — saved a Gemini call)
    HIGH_FIT/MAYBE → score_job → [should_continue?]
      YES → research_company → tailor_resume → write_cover_letter → prep_interview → END
      NO  → END (job scored below threshold)

The triage_job node uses TypeSafe's Jev decision model (~150ms, $0.04/M tokens)
to pre-filter jobs before the expensive Gemini scoring pipeline fires.
If TYPESAFE_API_KEY is not configured, triage passes everything through
and the pipeline behaves exactly as before.
"""

from langgraph.graph import StateGraph, START, END
from state import PipelineState
from nodes.resume_parser import parse_resume
from nodes.job_triage import triage_job
from nodes.job_scorer import score_job
from nodes.company_researcher import research_company
from nodes.resume_tailor import tailor_resume
from nodes.cover_letter import write_cover_letter
from nodes.interview_prep import prep_interview
from config import settings


def should_triage(state: PipelineState) -> str:
    """Gate after Jev triage: skip if confidently irrelevant."""
    triage = state.get("triage")
    if triage and triage.skipped:
        return "skip"
    return "continue"


def should_continue(state: PipelineState) -> str:
    """Gate after Gemini scoring: only continue if worth applying."""
    score = state.get("score")
    if score and score.is_worth_applying:
        return "continue"
    return "skip"


def build_pipeline() -> StateGraph:
    """Build and compile the Greenroom pipeline graph."""

    graph = StateGraph(PipelineState)

    # Add all nodes
    graph.add_node("parse_resume", parse_resume)
    graph.add_node("triage_job", triage_job)
    graph.add_node("score_job", score_job)
    graph.add_node("research_company", research_company)
    graph.add_node("tailor_resume", tailor_resume)
    graph.add_node("write_cover_letter", write_cover_letter)
    graph.add_node("prep_interview", prep_interview)

    # Wire the flow
    graph.add_edge(START, "parse_resume")
    graph.add_edge("parse_resume", "triage_job")

    # Gate 1: Jev triage — skip irrelevant jobs before Gemini fires
    graph.add_conditional_edges(
        "triage_job",
        should_triage,
        {
            "continue": "score_job",
            "skip": END,
        },
    )

    # Gate 2: Gemini scoring — only prep jobs worth applying to
    graph.add_conditional_edges(
        "score_job",
        should_continue,
        {
            "continue": "research_company",
            "skip": END,
        },
    )

    # Sequential flow after both gates
    graph.add_edge("research_company", "tailor_resume")
    graph.add_edge("tailor_resume", "write_cover_letter")
    graph.add_edge("write_cover_letter", "prep_interview")
    graph.add_edge("prep_interview", END)

    return graph.compile()


# Singleton — import this from anywhere
pipeline = build_pipeline()