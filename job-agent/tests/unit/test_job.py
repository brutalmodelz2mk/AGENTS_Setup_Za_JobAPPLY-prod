"""Unit tests for job normalization and deduplication."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.models.job import deduplicate_jobs, normalize_job


def test_normalize_keeps_known_fields():
    raw = {
        "title": "Backend Engineer",
        "company_name": "Acme",
        "apply_url": "https://acme.example/apply",
        "skills": "python, fastapi",
    }
    job = normalize_job(raw, source="greenhouse")
    assert job.title == "Backend Engineer"
    assert job.company == "Acme"
    assert job.url == "https://acme.example/apply"
    assert job.skills == ["python", "fastapi"]


def test_normalize_uses_null_when_unavailable():
    raw = {"title": "Some Role", "company_name": "Acme"}
    job = normalize_job(raw)
    assert job.location is None          # not guessed
    assert job.salary_min is None        # not guessed
    assert job.dedup_key() == "custom|acme|some role"


def test_dedup_removes_duplicates_and_preserves_order():
    a = {"source": "custom", "external_id": "1", "title": "X", "company": "Acme"}
    b = {"source": "custom", "external_id": "2", "title": "Y", "company": "Beta"}
    dup_a = dict(a)
    out = deduplicate_jobs([normalize_job(a), normalize_job(b), normalize_job(dup_a)])
    assert len(out) == 2
    assert out[0].external_id == "1"
    assert out[1].external_id == "2"
