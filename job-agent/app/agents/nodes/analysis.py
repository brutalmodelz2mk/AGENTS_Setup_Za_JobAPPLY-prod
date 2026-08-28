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
        try:
            analysis = await default_client.chat_schema(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract structured job facts from the description. "
                            "Return ONLY facts present in the text; use null for "
                            "anything unknown. Never infer or guess."
                        ),
                    },
                    {"role": "user", "content": str(job.get("description"))},
                ],
                schema=EXTRACTION_SCHEMA,
                model=settings.model_extraction or settings.openrouter_model,
            )
            # Prefer the strict LLM output but keep the probe URL if known.
            if not analysis.get("application_url") and job.get("url"):
                analysis["application_url"] = job["url"]
        except LLMError as exc:
            logger.warning("LLM extraction failed, falling back: %s", exc)
            analysis = _structure_preserving(job)
    else:
        analysis = _structure_preserving(job)

    return {"selected_job": job, "job_analysis": analysis}
