"""Repository for the `jobs` and `job_matches` tables."""
from __future__ import annotations

from typing import Any

from app.database.supabase import get_supabase
from app.models.job import Job


def upsert_job(job: Job) -> dict[str, Any]:
    """Insert or update a job keyed by (source, external_id)."""
    client = get_supabase()
    payload = {
        "source": job.source,
        "external_id": job.external_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "description": job.description,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "employment_type": job.employment_type,
        "remote_type": job.remote_type,
        "posted_at": job.posted_at,
    }
    # Upsert on the (source, external_id) unique constraint.
    data = (
        client.table("jobs")
        .upsert(payload, on_conflict="source,external_id")
        .execute()
    )
    return data.data[0] if data.data else payload


def list_jobs(limit: int = 50, **filters: Any) -> list[dict[str, Any]]:
    client = get_supabase()
    query = client.table("jobs").select("*").limit(limit)
    for key, value in filters.items():
        query = query.eq(key, value)
    data = query.execute()
    return data.data or []


def record_match(
    user_id: str,
    job_id: str,
    score: float,
    match_level: str,
    reasons: list[str],
    missing_req: list[str],
    recommended: bool,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    client = get_supabase()
    payload = {
        "user_id": user_id,
        "job_id": job_id,
        "score": score,
        "match_level": match_level,
        "reasons": reasons,
        "missing_req": missing_req,
        "recommended": recommended,
        "analysis": analysis,
    }
    data = client.table("job_matches").insert(payload).execute()
    return data.data[0] if data.data else payload
