"""
Greenroom LangGraph pipeline.

Flow:
  parse_resume → score_job → [should_continue?]
    YES → research_company → tailor_resume → write_cover_letter → prep_interview → END
    NO  → END (skip — job not worth applying to)

Phase 4 upgrade path:
  research_company and tailor_resume will run in parallel via Send().
  The state schema already supports this — no changes needed to nodes.
"""

from langgraph.graph import StateGraph, START, END
from state import PipelineState
from nodes.resume_parser import parse_resume
from nodes.job_scorer import score_job
from nodes.company_researcher import research_company
from nodes.resume_tailor import tailor_resume
from nodes.cover_letter import write_cover_letter
from nodes.interview_prep import prep_interview
from config import settings


def should_continue(state: PipelineState) -> str:
    """Gate: only continue if the job is worth applying to."""
    score = state.get("score")
    if score and score.is_worth_applying:
        return "continue"
    return "skip"


def build_pipeline() -> StateGraph:
    """Build and compile the Greenroom pipeline graph."""

    graph = StateGraph(PipelineState)

    # Add all nodes
    graph.add_node("parse_resume", parse_resume)
    graph.add_node("score_job", score_job)
    graph.add_node("research_company", research_company)
    graph.add_node("tailor_resume", tailor_resume)
    graph.add_node("write_cover_letter", write_cover_letter)
    graph.add_node("prep_interview", prep_interview)

    # Wire the flow
    graph.add_edge(START, "parse_resume")
    graph.add_edge("parse_resume", "score_job")

    # Conditional gate after scoring
    graph.add_conditional_edges(
        "score_job",
        should_continue,
        {
            "continue": "research_company",
            "skip": END,
        },
    )

    # Sequential flow after the gate
    # (Phase 4: research_company and tailor_resume become parallel via Send())
    graph.add_edge("research_company", "tailor_resume")
    graph.add_edge("tailor_resume", "write_cover_letter")
    graph.add_edge("write_cover_letter", "prep_interview")
    graph.add_edge("prep_interview", END)

    return graph.compile()


# Singleton — import this from anywhere
pipeline = build_pipeline()
