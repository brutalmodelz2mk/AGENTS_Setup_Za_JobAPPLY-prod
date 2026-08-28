"""Health endpoint (spec §23 Phase 1)."""
from __future__ import annotations

from fastapi import APIRouter

from app import AGENT_NAME, __version__
from app.config import settings
from app.database.redis import UpstashRedis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe. Never raises; reports configuration status."""
    redis_ok = False
    if settings.is_redis_configured:
        redis_ok = await UpstashRedis().ping()
    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "version": __version__,
        "environment": settings.environment,
        "llm_configured": settings.is_llm_configured,
        "supabase_configured": bool(settings.supabase_url and settings.supabase_service_role_key),
        "redis_configured": settings.is_redis_configured,
        "redis_ok": redis_ok,
    }


@router.get("/health/redis")
async def redis_health() -> dict:
    """Verify Redis read/write connectivity."""
    r = UpstashRedis()
    if not r.configured:
        return {"configured": False, "ok": False, "error": "UPSTASH_REDIS_URL/TOKEN not set"}
    ok = await r.ping()
    if ok:
        await r.set("dzvonko:health", "ok", ex=60)
        val = await r.get("dzvonko:health")
        return {"configured": True, "ok": val == "ok", "value": val}
    return {"configured": True, "ok": False, "error": "Redis PING failed"}
