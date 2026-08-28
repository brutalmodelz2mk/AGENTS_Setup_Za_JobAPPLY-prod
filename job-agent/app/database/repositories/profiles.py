"""Repository for the `user_profiles` table (source of truth for CV facts)."""
from __future__ import annotations

from typing import Any

from app.database.supabase import get_supabase
from app.models.profile import UserProfile


def _ensure_user(user_id: str, email: str | None = None) -> None:
    """Make sure a matching `users` row exists for the auth user (idempotent).

    The `users` table mirrors auth.users; a user_profile FK requires it. This
    keeps the repo self-sufficient without a DB trigger.
    """
    client = get_supabase()
    payload: dict[str, Any] = {"id": user_id}
    if email:
        payload["email"] = email
    client.table("users").upsert(payload, on_conflict="id").execute()


def get_profile(user_id: str) -> UserProfile | None:
    client = get_supabase()
    data = (
        client.table("user_profiles")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = data.data or []
    if not rows:
        return None
    return UserProfile(**rows[0])


def upsert_profile(profile: UserProfile) -> dict[str, Any]:
    _ensure_user(profile.user_id, profile.email)
    client = get_supabase()
    payload = profile.model_dump()
    payload.pop("user_id", None)
    data = (
        client.table("user_profiles")
        .upsert(
            {"user_id": profile.user_id, **payload},
            on_conflict="user_id",
        )
        .execute()
    )
    return data.data[0] if data.data else {"user_id": profile.user_id, **payload}
