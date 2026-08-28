"""Run the Dzvonko workflow (trigger + inspect state)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.graph import build_graph

router = APIRouter(prefix="/runs", tags=["runs"])


class RunRequest(BaseModel):
    user_id: str
    search_query: str = ""
    source: str = "manual"
    filters: dict[str, Any] = {}
    human_approved: bool = False
    human_confirm_submit: bool = False


@router.post("")
async def start_run(req: RunRequest) -> dict[str, Any]:
    """Execute the full LangGraph workflow for a user and return the final state."""
    graph = build_graph()
    state: dict[str, Any] = {
        "user_id": req.user_id,
        "search_query": req.search_query,
        "source": req.source,
        "filters": req.filters,
        "human_approved": req.human_approved,
        "human_confirm_submit": req.human_confirm_submit,
    }
    try:
        result = await graph.ainvoke(state)
    except Exception as exc:  # noqa: BLE001 - surface a clean 500
        raise HTTPException(status_code=500, detail=f"workflow failed: {exc}") from exc
    return result


@router.get("/health")
async def run_health() -> dict:
    """Cheap probe that the graph compiles without hitting external services."""
    try:
        build_graph()
        return {"graph": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"graph": "error", "detail": str(exc)}
