"""Job analysis node (spec §5, Phase 3).

Extracts structured facts from a job's description. When the LLM is configured
it uses a strict JSON-schema extraction; otherwise it copies known fields and
sets the rest to null. Unavailable information is represented as null — never
a guessed value (spec §5).
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.state import AgentState
from app.config import settings
from app.llm.openrouter import LLMError, default_client

logger = logging.getLogger("dzvonko.analysis")

FIELDS = [
    "title", "company", "location", "remote_type", "employment_type",
    "salary_min", "salary_max", "required_skills", "preferred_skills",
    "experience_requirement", "education_requirement", "application_url",
]

EXTRACTION_SCHEMA = {
    "name": "job_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "title": {"type": ["string", "null"]},
            "company": {"type": ["string", "null"]},
            "location": {"type": ["string", "null"]},
            "remote_type": {"type": ["string", "null"], "enum": ["remote", "hybrid", "on-site", "null"]},
            "employment_type": {"type": ["string", "null"], "enum": ["full-time", "part-time", "contract", "internship", "null"]},
            "salary_min": {"type": ["number", "null"]},
            "salary_max": {"type": ["number", "null"]},
            "required_skills": {"type": "array", "items": {"type": "string"}},
            "preferred_skills": {"type": "array", "items": {"type": "string"}},
            "experience_requirement": {"type": ["string", "null"]},
            "education_requirement": {"type": ["string", "null"]},
            "application_url": {"type": ["string", "null"]},
        },
        "required": FIELDS[:4] + ["required_skills", "preferred_skills"],
        "additionalProperties": False,
    },
}


def _normalize_analysis(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a model's job-analysis dict onto our canonical schema.

    Free-tier OpenRouter models frequently ignore strict json_schema and return
    their own field names. We tolerate aliases and always set missing fields to
    None (never guessed) so scoring/downstream stay deterministic.
    """
    def first(*keys: str) -> Any:
        for k in keys:
            for kk in (k, k.lower(), k.upper(), k.replace("-", "_").lower()):
                if kk in raw and raw[kk] not in (None, ""):
                    return raw[kk]
        return None

    # remote_type normalization
    remote_type = first("remote_type")
    if not remote_type:
        rem = first("remote")
        if isinstance(rem, bool):
            remote_type = "remote" if rem else "on-site"
        elif rem:
            remote_type = str(rem).lower()
    if not remote_type:
        arrangement = first("work_arrangement", "work_model", "working_model")
        if arrangement:
            a = str(arrangement).lower()
            remote_type = "remote" if "remote" in a else ("hybrid" if "hybrid" in a else "on-site")

    # salary normalization (handle both top-level and nested salary dict)
    salary_min = first("salary_min", "min_salary")
    salary_max = first("salary_max", "max_salary")
    if salary_min is None or salary_max is None:
        sal = first("salary")
        if isinstance(sal, dict):
            salary_min = salary_min or sal.get("min") or sal.get("low") or sal.get("min_salary")
            salary_max = salary_max or sal.get("max") or sal.get("high") or sal.get("max_salary")
        elif isinstance(sal, (int, float)):
            salary_min = salary_min or float(sal)

    return {
        "title": first("title", "role", "job_title"),
        "company": first("company", "company_name", "organization"),
        "location": first("location", "site", "city"),
        "remote_type": remote_type,
        "employment_type": first("employment_type", "job_type", "type", "contract_type"),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "required_skills": [s for s in (first("required_skills", "required_skill", "skills", "must_have") or []) if s],
        "preferred_skills": [s for s in (first("preferred_skills", "preferred_skill", "nice_to_have", "skills") or []) if s],
        "experience_requirement": first("experience_requirement", "experience_required", "experience", "years_experience"),
        "education_requirement": first("education_requirement", "education_required", "education"),
        "application_url": first("application_url", "url", "apply_url", "application_link"),
    }


def _structure_preserving(job: dict[str, Any]) -> dict[str, Any]:
    """Fallback: keep known fields, all else null. Never guesses."""
    skills = job.get("skills") or []
    return {
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "remote_type": job.get("remote_type"),
        "employment_type": job.get("employment_type"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "required_skills": list(skills),
        "preferred_skills": [],
        "experience_requirement": job.get("experience_requirement"),
        "education_requirement": job.get("education_requirement"),
        "application_url": job.get("url") or job.get("application_url"),
    }


def select_job(state: AgentState) -> dict[str, Any]:
    """Pick the candidate job to analyze (first by default)."""
    return state.get("selected_job") or (state.get("jobs") or [{}])[0]


async def analyze_job(state: AgentState) -> AgentState:
    job = select_job(state)
    if isinstance(job, dict):
        job = {"source": state.get("source", "manual"), **job}

    if settings.is_llm_configured and job.get("description"):
        extract_model = settings.model_extraction or settings.openrouter_model
        sys_msg = (
            "Extract structured job facts from the description. Return a JSON object. "
            "Use ONLY these exact keys, null for anything unknown, never invent: "
            "title, company, location, remote_type, employment_type, salary_min, "
            "salary_max, required_skills, preferred_skills, experience_requirement, "
            "education_requirement, application_url."
        )
        msgs = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": str(job.get("description"))},
        ]
        analysis = None
        try:
            analysis = await default_client.chat_schema(
                messages=msgs, schema=EXTRACTION_SCHEMA, model=extract_model
            )
        except LLMError:
            try:
                analysis = await default_client.chat_json(
                    messages=msgs, model=extract_model
                )
            except LLMError as exc:
                logger.warning("LLM extraction failed, falling back: %s", exc)
                analysis = _structure_preserving(job)
    else:
        analysis = _structure_preserving(job)

    analysis = _normalize_analysis(analysis)
    # Prefer the probe URL if the model didn't recover it.
    if not analysis.get("application_url") and job.get("url"):
        analysis["application_url"] = job["url"]

    return {"selected_job": job, "job_analysis": analysis}
