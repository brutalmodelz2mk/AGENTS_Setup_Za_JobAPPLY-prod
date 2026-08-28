"""Repository for the `user_profiles` table (source of truth for CV facts)."""
from __future__ import annotations

from typing import Any

from app.database.supabase import get_supabase
from app.models.profile import UserProfile


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
