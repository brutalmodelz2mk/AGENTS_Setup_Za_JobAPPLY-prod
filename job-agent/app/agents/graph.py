"""LangGraph workflow for Dzvonko (spec §4).

End-to-end: load profile → discover → dedupe → analyze → score →
prepare application → human review → open → fill → validate →
human confirm → submit → record result → send follow-up (if enabled).

Human-in-the-loop enforcement (spec §19): the workflow politely stops at
`human_review` and `human_confirm_submit` whenever the corresponding flags are
not set, and `submit_application` refuses to mark a submission unless approval
and confirmation are both present.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import application as app_nodes
from app.agents.nodes.analysis import analyze_job
from app.agents.nodes.discovery import deduplicate_jobs_node, discover_jobs
from app.agents.nodes.profile import load_user_profile
from app.agents.nodes.scoring import score_job_node
from app.agents.state import AgentState


# -- conditional edges ---------------------------------------------------------
def _after_profile(state: AgentState) -> str:
    return "end" if state.get("error") else "continue"


def _after_score(state: AgentState) -> str:
    return "recommended" if state.get("recommended") else "end"


def _after_review(state: AgentState) -> str:
    return "approved" if state.get("human_approved") else "end"


def _after_confirm(state: AgentState) -> str:
    return "confirmed" if state.get("human_confirm_submit") else "end"


def _after_validate(state: AgentState) -> str:
    # If a security challenge appeared, never proceed to confirmation.
    if state.get("browser_status") == "security_challenge":
        return "end"
    return "confirmed"


def build_graph() -> Any:
    builder = StateGraph(AgentState)

    builder.add_node("load_user_profile", load_user_profile)
    builder.add_node("discover_jobs", discover_jobs)
    builder.add_node("deduplicate_jobs", deduplicate_jobs_node)
    builder.add_node("analyze_job", analyze_job)
    builder.add_node("score_job", score_job_node)
    builder.add_node("prepare_application", app_nodes.prepare_application)
    builder.add_node("human_review", app_nodes.human_review)
    builder.add_node("open_application", app_nodes.open_application)
    builder.add_node("fill_application", app_nodes.fill_application)
    builder.add_node("validate_application", app_nodes.validate_application)
    builder.add_node("human_confirm_submit", app_nodes.human_confirm_submit)
    builder.add_node("submit_application", app_nodes.submit_application)
    builder.add_node("record_result", app_nodes.record_result)
    builder.add_node("send_followup", app_nodes.send_followup_if_enabled)

    builder.add_edge(START, "load_user_profile")
    builder.add_conditional_edges(
        "load_user_profile", _after_profile, {"continue": "discover_jobs", "end": END}
    )
    builder.add_edge("discover_jobs", "deduplicate_jobs")
    builder.add_edge("deduplicate_jobs", "analyze_job")
    builder.add_edge("analyze_job", "score_job")
    builder.add_conditional_edges(
        "score_job", _after_score, {"recommended": "prepare_application", "end": END}
    )
    builder.add_edge("prepare_application", "human_review")
    builder.add_conditional_edges(
        "human_review", _after_review, {"approved": "open_application", "end": END}
    )
    builder.add_edge("open_application", "fill_application")
    builder.add_edge("fill_application", "validate_application")
    builder.add_conditional_edges(
        "validate_application", _after_validate, {"confirmed": "human_confirm_submit", "end": END}
    )
    builder.add_conditional_edges(
        "human_confirm_submit", _after_confirm, {"confirmed": "submit_application", "end": END}
    )
    builder.add_edge("submit_application", "record_result")
    builder.add_edge("record_result", "send_followup")
    builder.add_edge("send_followup", END)

    return builder.compile()


# Compiled graph (singleton). Construct fresh instances for isolated runs.
graph = build_graph()
