"""Job resource endpoints (list / ingest jobs)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.database.repositories.jobs import list_jobs, upsert_job
from app.models.job import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def get_jobs(limit: int = 50) -> list[dict[str, Any]]:
    """List stored jobs (requires Supabase to be configured & migrated)."""
    try:
        return list_jobs(limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Supabase unavailable: {exc}") from exc


@router.post("")
async def create_job(job: Job) -> dict[str, Any]:
    """Ingest a single job record (normalized + persisted)."""
    return upsert_job(job)
