"""Playwright client (spec §5, §16).

Rules enforced here:
- Prefer accessible roles/labels and stable selectors.
- Wait for actual page state; never sleep() as the primary wait.
- Screenshot + diagnostics on failure.
- Detect CAPTCHA/MFA/security challenges and STOP — never bypass.
- Final submission requires explicit human confirmation (checked by the node).
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from app.config import settings

logger = logging.getLogger("dzvonko.browser")

# Signatures of security challenges we must never attempt to circumvent.
_CHALLENGE_PATTERNS = re.compile(
    r"captcha|cloudflare|cf-challenge|access denied|verify you are human|"
    r"recaptcha|i am not a robot|enter the code|two-factor|2fa|authenticator|"
    r"sms code|security check|multi-factor",
    re.IGNORECASE,
)
_MFA_SELECTORS = [
    "input[name*=totp i]", "input[name*=otp i]", "input[autocomplete=one-time-code]",
    "form[data-test*=mfa i]", "iframe[src*=recaptcha i]",
]


class BrowserResult(dict[str, Any]):
    pass


def _challenge_detected(page: Any) -> str | None:
    """Return a challenge reason if one is present on the page, else None."""
    try:
        text = page.locator("body").inner_text(timeout=2000)
    except Exception:  # noqa: BLE001
        text = ""
    if _CHALLENGE_PATTERNS.search(text or ""):
        return "captcha_or_mfa"
    for sel in _MFA_SELECTORS:
        try:
            if page.locator(sel).count() > 0:
                return "mfa"
        except Exception:  # noqa: BLE001
            continue
    return None


class PlaywrightBrowser:
    """Thin, guarded wrapper around Playwright page operations."""

    def __init__(self, headless: bool | None = None, timeout_ms: int | None = None) -> None:
        self.headless = settings.browser_headless if headless is None else headless
        self.timeout_ms = settings.browser_timeout_ms if timeout_ms is None else timeout_ms
        self._pw: Any | None = None
        self._browser: Any | None = None
        self.page: Any | None = None

    async def start(self) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # playwright not installed
            raise RuntimeError(
                "Playwright is not installed. Run `pip install playwright && "
                "playwright install chromium` to enable browser automation."
            ) from exc
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        context = await self._browser.new_context()
        self.page = await context.new_page()

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._browser = None
        self._pw = None

    async def open(self, url: str) -> str:
        """Open a URL, wait for load, and report the resulting status."""
        if self.page is None:
            await self.start()
        page = self.page
        assert page is not None
        await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        chall = _challenge_detected(page)
        if chall:
            return f"security_challenge:{chall}"
        return "opened"

    async def fill(self, fields: dict[str, str]) -> str:
        """Fill mapped fields using get_by_label / get_by_role / get_by_placeholder.

        Uses the first matching strategy; never guesses arbitrary selectors.
        """
        if self.page is None:
            raise RuntimeError("Browser not started; call open() first.")
        page = self.page
        for label, value in fields.items():
            try:
                locator = (
                    page.get_by_label(re.compile(re.escape(label), re.I))
                    .or_(page.get_by_placeholder(re.compile(re.escape(label), re.I)))
                    .or_(page.get_by_role("textbox", name=re.compile(re.escape(label), re.I)))
                )
            except Exception:  # noqa: BLE001
                locator = None
            if locator is None:
                continue
            try:
                await locator.first.fill(value, timeout=self.timeout_ms)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not fill field %r: %s", label, exc)
        return "filled"

    async def screenshot(self, path: str) -> None:
        if self.page:
            try:
                await self.page.screenshot(path=path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Screenshot failed: %s", exc)

    async def submit(self) -> str:
        """Click the primary submit / apply button. Confirmation is enforced by the node."""
        if self.page is None:
            raise RuntimeError("Browser not started.")
        page = self.page
        for role, name in [("button", "submit"), ("button", "apply"), ("button", "continue")]:
            try:
                locator = page.get_by_role(role, name=re.compile(name, re.I)).first
                await locator.click(timeout=self.timeout_ms)
                return "submitted"
            except Exception:  # noqa: BLE001
                continue
        return "no_submit_button"
