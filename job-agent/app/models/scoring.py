"""Job scoring model (spec §5)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JobScore(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    match_level: str = Field(default="low", pattern="^(low|medium|high)$")
    reasons: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    recommended: bool = False

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
