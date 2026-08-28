"""Typed LangGraph state for the Dzvonko workflow (spec §6).

Keep state small and serializable. Never place passwords, API keys, cookies,
or sensitive browser credentials here.
"""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Identity / context
    user_id: str
    search_query: str
    source: str  # e.g. "linkedin", "greenhouse", "custom"
    filters: dict[str, Any]

    # Discovery
    jobs: list[dict[str, Any]]

    # Analysis + scoring
    selected_job: dict[str, Any] | None
    job_analysis: dict[str, Any] | None
    match_score: float
    match_level: str  # "low" | "medium" | "high"
    scoring: dict[str, Any] | None
    recommended: bool  # True if analysis passed the score threshold

    # Application preparation
    application_data: dict[str, Any] | None

    # Browser (Phase 5)
    browser_status: str  # "idle" | "opened" | "filled" | "captcha" | "error"
    browser_error: str | None

    # Human-in-the-loop
    human_approved: bool  # application reviewed + approved
    human_confirm_submit: bool  # final submission confirmed

    # Outcome
    submission_status: str  # "none" | "submitted" | "cancelled" | "error"
    submitted_at: str | None
    error: str | None
