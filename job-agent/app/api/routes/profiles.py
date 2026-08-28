"""User profile endpoints (spec §5: user facts are the source of truth)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database.repositories.profiles import get_profile, upsert_profile
from app.models.profile import UserProfile

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileIn(BaseModel):
    user_id: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    skills: list[str] = []
    experience: list[dict[str, Any]] = []
    education: list[dict[str, Any]] = []
    certifications: list[str] = []
    languages: list[str] = []
    salary_expectation: float | None = None
    remote_preference: str | None = None
    cv_url: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None

    def to_model(self) -> UserProfile:
        return UserProfile(**self.model_dump())


@router.get("/{user_id}")
async def read_profile(user_id: str) -> dict[str, Any]:
    profile = get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile.model_dump()


@router.put("/{user_id}")
async def write_profile(user_id: str, payload: ProfileIn) -> dict[str, Any]:
    if payload.user_id != user_id:
        raise HTTPException(status_code=400, detail="user_id mismatch")
    data = upsert_profile(payload.to_model())
    return data
