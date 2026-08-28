"""User profile model (spec §5, §8).

The user's real facts are the single source of truth. The agent must never
invent employment history, education, certifications, skills, employers, dates
or achievements (spec §5 "Application Preparation").
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

ExperienceItem = dict[str, Any]  # {company, role, start_date, end_date, ...}
EducationItem = dict[str, Any]  # {school, degree, field, year, ...}


class UserProfile(BaseModel):
    user_id: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    salary_expectation: float | None = None
    remote_preference: str | None = None
    cv_url: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None

    @field_validator("skills", "certifications", "languages", mode="before")
    @classmethod
    def _split_str(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if v is None:
            return []
        return list(v)

    @property
    def skillset_lower(self) -> set[str]:
        return {s.lower().strip() for s in self.skills if s}
