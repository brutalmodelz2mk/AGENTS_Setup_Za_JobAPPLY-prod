"""Integration tests for the LangGraph workflow (spec §4, §19)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import app.agents.nodes.application as app_nodes
import app.agents.nodes.discovery as discovery
import app.agents.nodes.scoring as scoring
from app.agents.graph import build_graph
from app.agents.nodes.application import submit_application
from app.models.profile import UserProfile


class FakeBrowser:
    """Deterministic stand-in for Playwright (no real browser in tests)."""

    def __init__(self) -> None:
        self.opened = False

    async def open(self, url: str) -> str:
        self.opened = True
        return "opened"

    async def fill(self, fields: dict) -> str:
        return "filled"

    async def submit(self) -> str:
        return "submitted"


def _sample_job() -> dict:
    return {
        "source": "custom",
        "external_id": "1",
        "title": "Backend Engineer",
        "company": "Acme",
        "description": "python fastapi postgres",
        "skills": "python,fastapi,postgres",
        "remote_type": "remote",
        "url": "https://acme.example/apply",
    }


async def _fake_fetch(source: str, url: str | None = None) -> list:
    return [_sample_job()]


async def test_graph_compiles_and_early_stops_without_profile():
    graph = build_graph()
    result = await graph.ainvoke({"user_id": "u1", "source": "custom"})
    # No profile → not recommended → workflow stops before application.
    assert result.get("submission_status") in (None, "")


async def test_graph_human_in_the_loop_enforced(monkeypatch):
    """Even a recommended job must NOT be submitted without human approval."""
    prof = UserProfile(user_id="u1", skills=["python", "fastapi", "postgres"], remote_preference="remote")
    monkeypatch.setattr(scoring, "get_profile", lambda user_id: prof)
    monkeypatch.setattr(app_nodes, "get_profile", lambda user_id: prof)
    monkeypatch.setattr(app_nodes, "_get_browser", FakeBrowser)
    monkeypatch.setattr(discovery, "fetch_jobs_from_source", _fake_fetch)

    graph = build_graph()
    result = await graph.ainvoke({"user_id": "u1", "source": "custom"})
    # human_approved is False by default → must stop, never submit.
    assert result.get("submission_status") != "submitted"
    assert result.get("recommended") is True


async def test_submit_marks_submitted_when_gated(monkeypatch):
    monkeypatch.setattr(app_nodes, "_get_browser", FakeBrowser)
    state = {
        "user_id": "u1",
        "human_approved": True,
        "human_confirm_submit": True,
        "browser_status": "filled",
        "application_data": {"cover_letter": "x"},
    }
    result = await submit_application(state)
    assert result["submission_status"] == "submitted"


async def test_submit_requires_both_flags():
    state = {"user_id": "u1", "human_approved": True, "human_confirm_submit": False, "browser_status": "filled"}
    result = await submit_application(state)
    assert result["submission_status"] == "cancelled"
