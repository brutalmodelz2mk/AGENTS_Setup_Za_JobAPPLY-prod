"""Job model + normalization helpers (spec §5)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class Job(BaseModel):
    source: str = "custom"
    external_id: str | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    url: str | None = None
    description: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    posted_at: str | None = None
    skills: list[str] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def _skills_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if v is None:
            return []
        return list(v)

    def dedup_key(self) -> str:
        """Deterministic key used to avoid duplicate jobs.

        Uses source + external_id when available, else source + normalized
        company+title. Absent fields degrade gracefully instead of being guessed.
        """
        company = (self.company or "").lower().strip()
        title = (self.title or "").lower().strip()
        if self.external_id:
            ident = str(self.external_id)
        else:
            ident = f"{company}|{title}"
        return f"{self.source}|{ident}"


def _first(*values: Any) -> Any:
    for v in values:
        if v not in (None, ""):
            return v
    return None


def normalize_job(raw: dict[str, Any], source: str = "custom") -> Job:
    """Coerce an arbitrary record into a Job.

    Missing values become None (never guessed). Source is the provenance of
    the listing, used for deduplication.
    """
    return Job(
        source=raw.get("source") or source,
        external_id=raw.get("external_id") or raw.get("id") or raw.get("externalId"),
        title=raw.get("title"),
        company=_first(raw.get("company"), raw.get("company_name")),
        location=raw.get("location"),
        url=_first(raw.get("url"), raw.get("apply_url"), raw.get("application_url")),
        description=raw.get("description") or raw.get("job_description"),
        salary_min=raw.get("salary_min") or raw.get("salaryMin"),
        salary_max=raw.get("salary_max") or raw.get("salaryMax"),
        employment_type=raw.get("employment_type"),
        remote_type=raw.get("remote_type"),
        posted_at=raw.get("posted_at") or raw.get("postedAt"),
        skills=raw.get("skills") or [],
    )


def deduplicate_jobs(jobs: list[Any]) -> list[Any]:
    """Remove duplicate jobs by dedup key, preserving first-seen order."""
    seen: set[str] = set()
    out: list[Any] = []
    for job in jobs:
        key = job.dedup_key() if isinstance(job, Job) else normalize_job(job).dedup_key()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out
