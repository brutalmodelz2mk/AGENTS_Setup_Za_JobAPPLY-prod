"""OpenRouter client (OpenAI-compatible) — spec §7.

Wraps the chat-completions endpoint and adds a structured-JSON helper.
All credentials come from Settings (never hard-coded). Sensitive headers and
keys are never logged.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("dzvonko.llm")

# OpenRouter returns an OpenAI-compatible payload if we do not pass
# "OpenAI-Beta: assistants=v1". Standard chat/completions is what we want.


class LLMError(RuntimeError):
    """Raised for any non-recoverable LLM gateway failure."""


class OpenRouterClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")

    # -- internal -----------------------------------------------------------
    def _headers_for(self, key: str | None = None) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {key or self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.http_referer,
            "X-Title": settings.x_title,
            "User-Agent": "dzvonko-agent/0.1.0",
        }

    # -- public -------------------------------------------------------------
    async def aclose(self) -> None:
        # Compatibility no-op — each call uses its own short-lived client.
        return None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Send a chat request and return the assistant message text.

        Rotates to the next spare key on auth (401) / rate-limit (429) failures.
        """
        if not self.api_key:
            raise LLMError("OPENROUTER_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": model or settings.openrouter_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format
        payload.update(kwargs)

        url = f"{self.base_url}/chat/completions"
        keys = [self.api_key] + [k for k in settings.rotation_keys if k != self.api_key]

        last_err: LLMError | None = None
        for attempt, key in enumerate(keys):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(url, headers=self._headers_for(key), json=payload)
            except httpx.HTTPError as exc:  # transient network errors
                logger.warning("LLM network error: %s", exc)
                raise LLMError(f"OpenRouter network error: {exc}") from exc

            if resp.status_code < 400:
                data = resp.json()
                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise LLMError("Malformed OpenRouter response") from exc

            # Rotate only on auth/rate-limit; never on bad-model (400/404).
            if resp.status_code in (401, 429) and attempt < len(keys) - 1:
                logger.warning(
                    "OpenRouter HTTP %s with key #%d — rotating to spare key",
                    resp.status_code, attempt + 1,
                )
                last_err = LLMError(f"OpenRouter HTTP {resp.status_code}")
                continue

            logger.error("OpenRouter HTTP %s for model=%s", resp.status_code, payload["model"])
            raise LLMError(f"OpenRouter HTTP {resp.status_code}")

        if last_err:
            raise last_err
        raise LLMError("OpenRouter request failed")

    async def chat_json(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Chat but force a JSON object reply and return it parsed."""
        text = await self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return _parse_json_object(text)

    async def chat_schema(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Chat with a strict JSON-schema response (OpenRouter structured output)."""
        text = await self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_schema", "json_schema": schema},
        )
        return _parse_json_object(text)


def _parse_json_object(text: str) -> dict[str, Any]:
    """Tolerant JSON parse that finds the first balanced JSON object."""
    if not isinstance(text, str) or not text.strip():
        raise LLMError("Empty LLM response while expecting JSON")
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        # Some models wrap JSON in triple-backtick fences or prose.
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise LLMError(f"Could not parse JSON from LLM response: {stripped[:200]!r}")


# Singleton for convenience; construct your own per-request if you prefer.
default_client = OpenRouterClient()
