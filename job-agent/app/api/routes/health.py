"""Health endpoint (spec §23 Phase 1)."""
from __future__ import annotations

from fastapi import APIRouter

from app import __version__, AGENT_NAME
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe. Never raises; reports configuration status."""
    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "version": __version__,
        "environment": settings.environment,
        "llm_configured": settings.is_llm_configured,
        "supabase_configured": bool(settings.supabase_url and settings.supabase_service_role_key),
    }
