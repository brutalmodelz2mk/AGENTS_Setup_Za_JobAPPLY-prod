"""Unit tests for deterministic job scoring."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents.nodes.scoring import score_job
from app.models.profile import UserProfile


def profile(skills: list[str], remote_preference: str = "remote") -> UserProfile:
    return UserProfile(user_id="u1", skills=skills, remote_preference=remote_preference)


def test_scoring_high_overlap_recommends():
    analysis = {"required_skills": ["python", "fastapi", "postgres"], "remote_type": "remote"}
    result = score_job(analysis, profile(["python", "fastapi", "postgres", "sql"]))
    assert result.recommended is True
    assert result.match_level in ("medium", "high")
    assert result.score >= 60


def test_scoring_no_skills_not_recommended():
    analysis = {"required_skills": []}
    result = score_job(analysis, profile([]))
    assert result.recommended is False


def test_scoring_missing_skills_listed():
    analysis = {"required_skills": ["go", "rust"]}
    result = score_job(analysis, profile(["python"]))
    assert set(result.missing_requirements) == {"go", "rust"}
    assert result.recommended is False


def test_scoring_no_profile_is_not_recommended():
    result = score_job({"required_skills": ["python"]}, None)
    assert result.recommended is False
    assert result.score == 0.0
