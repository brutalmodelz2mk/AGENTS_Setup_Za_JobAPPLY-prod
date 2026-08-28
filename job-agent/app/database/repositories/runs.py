"""Repository for `agent_runs` (observability, spec §17)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database.supabase import get_supabase


def start_run(user_id: str | None, workflow: str, run_id: str) -> dict[str, Any]:
    client = get_supabase()
    payload = {
        "user_id": user_id,
        "workflow": workflow,
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
    }
    data = client.table("agent_runs").insert(payload).execute()
    return data.data[0] if data.data else payload


def finish_run(
    run_db_id: str,
    status: str,
    error: str | None = None,
    node: str | None = None,
) -> None:
    client = get_supabase()
    payload: dict[str, Any] = {
        "status": status,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    if node:
        payload["node"] = node
    if error:
        payload["error"] = error
    client.table("agent_runs").update(payload).eq("id", run_db_id).execute()
