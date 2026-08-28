"""Job scoring node (spec §5, Phase 3).

Deterministic and explainable: the score is a weighted blend of skill overlap
and a few explicit checks, so its `reasons` and `missing_requirements` are
reproducible.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.state import AgentState
from app.database.repositories.profiles import get_profile
from app.models.profile import UserProfile
from app.models.scoring import JobScore

logger = logging.getLogger("dzvonko.scoring")

RECOMMEND_THRESHOLD = 60.0


def score_job(analysis: dict[str, Any], profile: UserProfile | None) -> JobScore:
    """Return an explainable JobScore for a job analysis against a profile."""
    if profile is None:
        # Without a profile we cannot honestly claim a match; score low, not recommended.
        return JobScore(
            score=0.0,
            match_level="low",
            reasons=["No user profile available for scoring"],
            missing_requirements=[],
            recommended=False,
        )

    required = [s.lower().strip() for s in (analysis.get("required_skills") or []) if s]
    profile_skills = profile.skillset_lower

    matched_skills: list[str] = []
    missing: list[str] = []
    for skill in required:
        # Match the exact skill or any profile skill that contains it.
        if any(skill in ps or ps in skill for ps in profile_skills):
            matched_skills.append(skill)
        else:
            missing.append(skill)

    score = 0.0
    reasons: list[str] = []

    if required:
        overlap = len(matched_skills) / len(required)
        score += overlap * 70
        reasons.append(
            f"{len(matched_skills)}/{len(required)} required skills matched"
        )
        if missing:
            reasons.append(f"Missing: {', '.join(missing[:6])}")
    else:
        score += 40  # no explicit skill list → neutral signal
        reasons.append("No explicit skill requirements listed")

    # Location / remote preference
    remote = (analysis.get("remote_type") or "").lower()
    pref = (profile.remote_preference or "").lower()
    if remote and pref and (remote == pref or (remote == "remote" and pref in ("remote", "any"))):
        score += 15
        reasons.append(f"Remote type matches preference ({remote})")
    else:
        # Not a hard penalty; only give partial credit for on-site jobs.
        score += 5 if remote else 0

    # Seniority / experience signal
    exp_req = (analysis.get("experience_requirement") or "").lower()
    if exp_req and any(tok in exp_req for tok in ["senior", "lead", "staff"]):
        score -= 5
        reasons.append("Senior-level requirement (may be above profile)")

    score = max(0.0, min(100.0, score))

    match_level = "high" if score >= 80 else ("medium" if score >= 60 else "low")
    recommended = score >= RECOMMEND_THRESHOLD
    return JobScore(
        score=round(score, 1),
        match_level=match_level,
        reasons=reasons,
        missing_requirements=missing[:10],
        recommended=recommended,
    )


async def score_job_node(state: AgentState) -> AgentState:
    profile: UserProfile | None = None
    user_id = state.get("user_id")
    if user_id:
        try:
            profile = get_profile(user_id)
        except Exception as exc:  # noqa: BLE001 - degrade to no-profile scoring
            logger.warning("Could not load profile for %s: %s", user_id, exc)
            profile = None

    analysis = state.get("job_analysis") or {}
    result = score_job(analysis, profile)
    return {
        "match_score": result.score,
        "match_level": result.match_level,
        "scoring": result.to_dict(),
        "recommended": result.recommended,
    }
