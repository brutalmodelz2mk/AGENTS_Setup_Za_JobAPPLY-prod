"""load_user_profile node (spec §4).

Ensures a known user_id is present before the pipeline runs. The full profile
is fetched lazily by the nodes that need it, keeping state small (§6).
"""
from __future__ import annotations

from app.agents.state import AgentState


async def load_user_profile(state: AgentState) -> AgentState:
    """Validate user_id; set an error if it is missing so the pipeline stops early."""
    if not state.get("user_id"):
        return {"error": "user_id is required to run the job pipeline"}
    # Optionally confirm the profile exists (not required to proceed).
    return {}
