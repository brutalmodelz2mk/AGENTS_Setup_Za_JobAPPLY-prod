"""Supabase client factory (spec §8).

The service-role key is used server-side only. If Supabase is not configured,
the app still boots (lazy accessors raise a clear error only when used).
"""
from __future__ import annotations

from typing import Any

from app.config import settings


class DatabaseConfigError(RuntimeError):
    """Raised when Supabase is accessed without being configured."""


def _client() -> Any:
    """Return a freshly-initialized Supabase client (lazy)."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise DatabaseConfigError(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in .env."
        )
    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover
        raise DatabaseConfigError("supabase package not installed") from exc
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase() -> Any:
    """Return a Supabase client for server-side (service role) access."""
    return _client()


def health_check() -> dict[str, bool]:
    """Cheap connectivity probe. Returns bools, never raises."""
    result = {"configured": False, "reachable": False}
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return result
    result["configured"] = True
    try:
        client = _client()
        client.table("jobs").select("id").limit(1).execute()
        result["reachable"] = True
    except Exception:  # noqa: BLE001 - health check must not raise
        result["reachable"] = False
    return result
