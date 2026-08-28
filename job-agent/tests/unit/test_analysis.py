"""Unit tests for the job-analysis normalizer (LLM field-name tolerance)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents.nodes.analysis import _normalize_analysis


def test_normalize_maps_model_aliases():
    raw = {
        "title": "Senior Backend Engineer",
        "role": "Backend Engineer",
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "work_arrangement": "remote-first",
        "salary": {"min": 50000, "max": 90000},
        "experience_required": "5+ years",
        "education_required": "BS",
    }
    out = _normalize_analysis(raw)
    assert out["title"] == "Senior Backend Engineer"
    assert out["remote_type"] == "remote"          # from work_arrangement
    assert out["required_skills"] == ["Python", "FastAPI", "PostgreSQL"]
    assert out["salary_min"] == 50000
    assert out["salary_max"] == 90000
    assert out["experience_requirement"] == "5+ years"
    assert out["education_requirement"] == "BS"


def test_normalize_remote_bool():
    out = _normalize_analysis({"title": "X", "remote": True})
    assert out["remote_type"] == "remote"


def test_normalize_unknown_fields_are_null_not_guessed():
    out = _normalize_analysis({"title": "X"})
    assert out["company"] is None
    assert out["salary_min"] is None
    assert out["remote_type"] is None
