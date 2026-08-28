"""Shared FastAPI dependencies."""
from __future__ import annotations

from app.database.supabase import get_supabase


def get_db_client():
    """FastAPI dependency that provides the service-role Supabase client."""
    return get_supabase()
