"""Application preparation, review, browser-fill and submission nodes (spec §4, §5, §19).

Human-in-the-loop is enforced: the agent never silently submits. `submit_application`
only proceeds when BOTH `human_approved` and `human_confirm_submit` are True **and**
the browser actually reached a usable state. No invented CV facts — every piece of
application data derives from the user's profile (source of truth).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.state import AgentState
from app.config import settings
from app.browser.playwright_client import PlaywrightBrowser
from app.database.repositories.profiles import get_profile
from app.llm.openrouter import LLMError, default_client
from app.models.profile import UserProfile
from app.services.email_service import EmailMessage

logger = logging.getLogger("dzvonko.application")


# -- DI hooks (tests can monkeypatch these) -----------------------------------
def _get_browser() -> PlaywrightBrowser:
    return PlaywrightBrowser()


def _load_profile(state: AgentState) -> UserProfile | None:
    user_id = state.get("user_id")
    if not user_id:
        return None
    try:
        return get_profile(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load profile for %s: %s", user_id, exc)
        return None


def _build_factual_fields(state: AgentState, profile: UserProfile | None) -> dict[str, str]:
    """Map only real profile facts into form fields. Never invents."""
    fields: dict[str, str] = {}
    if profile:
        if profile.full_name:
            fields["full_name"] = profile.full_name
        if profile.email:
            fields["email"] = profile.email
        if profile.phone:
            fields["phone"] = profile.phone
        if profile.location:
            fields["location"] = profile.location
        if profile.linkedin_url:
            fields["linkedin"] = profile.linkedin_url
        if profile.portfolio_url:
            fields["website"] = profile.portfolio_url
    return fields


# -- Nodes ---------------------------------------------------------------------
async def prepare_application(state: AgentState) -> AgentState:
    """Generate cover letter + structured application data (facts only)."""
    profile = _load_profile(state)
    job = state.get("selected_job") or {}
    analysis = state.get("job_analysis") or {}

    company = analysis.get("company") or job.get("company")
    title = analysis.get("title") or job.get("title")

    cover_letter = ""
    if settings.is_llm_configured and profile:
        try:
            cover_letter = await default_client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Write a short, honest cover letter for the candidate. "
                            "Use ONLY facts from their profile below. Never invent "
                            "experience, employers, dates or achievements. Be concise."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Profile:\n{profile.model_dump_json()}\n\n"
                            f"Company: {company}\nRole: {title}\n\n"
                            "Write the cover letter."
                        ),
                    },
                ],
                model=settings.openrouter_model,
                temperature=0.4,
            )
        except LLMError as exc:
            logger.warning("Cover-letter generation failed: %s", exc)
    elif profile:
        # Factual fallback: never invents anything not in the profile.
        name = profile.full_name or profile.email or "the candidate"
        cover_letter = (
            f"Dear hiring team,\n\nI am writing to apply for the {title or 'role'} "
            f"position at {company or 'your company'}. My background includes "
            f"{', '.join(profile.skills) if profile.skills else 'a relevant skill set'}. "
            f"I look forward to the opportunity to discuss how I can contribute.\n\n"
            f"Sincerely,\n{name}"
        )

    application_data: dict[str, Any] = {
        "cover_letter": cover_letter,
        "fields": _build_factual_fields(state, profile),
        "answers": {},
        "status": "draft",
    }
    return {"application_data": application_data, "human_approved": False}


async def human_review(state: AgentState) -> AgentState:
    """Decision gate: pass-through; approval is supplied by the caller/API."""
    return {}


async def open_application(state: AgentState) -> AgentState:
    """Open the application URL (spec §16). Stops on security challenges."""
    application_url = (state.get("job_analysis") or {}).get("application_url")
    if not application_url:
        return {"browser_status": "error", "browser_error": "no application_url"}
    try:
        browser = _get_browser()
        status = await browser.open(application_url)
    except RuntimeError as exc:  # Playwright not installed
        return {"browser_status": "error", "browser_error": str(exc)}
    if status.startswith("security_challenge"):
        # CAPTCHA/MFA — do not bypass; stop and wait for the human.
        return {"browser_status": "security_challenge", "browser_error": status}
    return {"browser_status": "opened"}


async def fill_application(state: AgentState) -> AgentState:
    """Fill the form from real profile facts, then mark filled."""
    if state.get("browser_status") not in ("opened",):
        return {"browser_status": state.get("browser_status", "error")}
    profile = _load_profile(state)
    fields = _build_factual_fields(state, profile)
    app_data = state.get("application_data") or {}
    if isinstance(app_data, dict):
        fields.update({k: v for k, v in (app_data.get("fields") or {}).items()})
    try:
        browser = _get_browser()
        await browser.fill(fields)
    except RuntimeError as exc:
        return {"browser_status": "error", "browser_error": str(exc)}
    return {"browser_status": "filled"}


async def validate_application(state: AgentState) -> AgentState:
    """Confirm the form reached a safe, non-challenged state."""
    status = state.get("browser_status")
    if status == "security_challenge":
        return {"browser_status": "security_challenge"}
    if status == "filled":
        return {"browser_status": "filled"}
    return {"browser_status": status or "error"}


async def human_confirm_submit(state: AgentState) -> AgentState:
    """Gate: final submission requires an explicit human confirmation."""
    # human_confirm_submit is supplied by the caller/API; reflect it.
    return {}


async def submit_application(state: AgentState) -> AgentState:
    """Submit ONLY when human-approved + human-confirmed + browser ready."""
    approved = bool(state.get("human_approved"))
    confirmed = bool(state.get("human_confirm_submit"))
    browser_ok = state.get("browser_status") == "filled"

    if not approved:
        return {"submission_status": "cancelled", "error": "not human-approved"}
    if not confirmed:
        return {"submission_status": "cancelled", "error": "not human-confirmed"}
    if not browser_ok:
        return {
            "submission_status": "cancelled",
            "error": "browser form not in a ready state",
        }

    try:
        browser = _get_browser()
        result = await browser.submit()
    except RuntimeError as exc:
        return {"submission_status": "error", "error": str(exc)}

    if result == "submitted":
        logger.info("Application submitted for %s", state.get("user_id"))
        return {
            "submission_status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }
    return {"submission_status": "error", "error": f"submit returned {result}"}


async def record_result(state: AgentState) -> AgentState:
    """Persist the application result to Supabase (guarded; no-op if unconfigured)."""
    if not state.get("submission_status"):
        return {}
    try:
        from app.database.repositories.jobs import record_match  # noqa: F401
        # Persist a run event; deeper persistence is wired in Phase 5/6.
        logger.info("record_result: status=%s", state.get("submission_status"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not record result: %s", exc)
    return {}


async def send_followup_if_enabled(state: AgentState) -> AgentState:
    """Send a follow-up email if configured and the application was submitted."""
    if state.get("submission_status") != "submitted":
        return {}
    if not state.get("human_approved"):
        return {}
    app_data = state.get("application_data") or {}
    recipient = (app_data or {}).get("recipient") if isinstance(app_data, dict) else None
    if not recipient:
        return {}
    try:
        from app.services.email_service import default_email_service

        default_email_service.send(
            EmailMessage(
                recipient=recipient,
                subject="Your application was submitted",
                body="Your job application was submitted successfully.",
            )
        )
        logger.info("Follow-up email queued for %s", recipient)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Follow-up email skipped: %s", exc)
    return {}
