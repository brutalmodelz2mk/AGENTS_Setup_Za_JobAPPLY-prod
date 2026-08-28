"""Job discovery node (spec §5, Phase 3).

Fetches listings from a configured source, normalizes records, and never
fabricates jobs. Official APIs/integrations are preferred (spec §1); manual
sources are opaque JSON records handed in via state.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.agents.state import AgentState
from app.models.job import deduplicate_jobs as _dedupe
from app.models.job import normalize_job

logger = logging.getLogger("dzvonko.discovery")


async def fetch_jobs_from_source(source: str, url: str | None = None) -> list[dict[str, Any]]:
    """Fetch raw job records from an HTTP source (e.g. a Greenhouse JSON feed).

    If source == 'manual' or no url, returns []. Missing/unparseable input
    yields [] — never fabricated listings.
    """
    if not url:
        return []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Source fetch failed for %s: %s", url, exc)
        return []

    if isinstance(payload, dict):
        jobs = payload.get("jobs") or payload.get("data") or []
    elif isinstance(payload, list):
        jobs = payload
    else:
        jobs = []
    return [job for job in jobs if isinstance(job, dict)]


async def discover_jobs(state: AgentState) -> AgentState:
    """Populate state['jobs'] with normalized records from the configured source."""
    source = state.get("source", "manual")
    url = (state.get("filters") or {}).get("url")
    raw = await fetch_jobs_from_source(source, url)

    jobs = [
        normalize_job(job, source=job.get("source") or source).model_dump()
        for job in raw
    ]
    logger.info("discover_jobs: %s -> %d raw, %d normalized", source, len(raw), len(jobs))
    return {"jobs": jobs}


async def deduplicate_jobs_node(state: AgentState) -> AgentState:
    """Remove duplicate jobs while preserving order (spec §5)."""
    jobs = state.get("jobs", [])
    unique = _dedupe(jobs)
    logger.info("deduplicate_jobs: %d -> %d", len(jobs), len(unique))
    return {"jobs": unique}
