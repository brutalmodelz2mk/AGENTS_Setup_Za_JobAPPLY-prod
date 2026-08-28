"""Pytest configuration: ensure the project root is importable + keep tests offline."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from app.llm.openrouter import LLMError, default_client  # noqa: E402


async def _llm_disabled(*args, **kwargs):
    """Deterministic stand-in: force the LLM fallback path in tests."""
    raise LLMError("LLM disabled for tests")


@pytest.fixture(autouse=True)
def _disable_llm(monkeypatch):
    """Never hit a real LLM during tests (free-tier is slow/flaky).

    The workflow nodes already degrade gracefully to their fallback path when
    the client raises LLMError, so tests stay fast and deterministic.
    """
    monkeypatch.setattr(default_client, "chat", _llm_disabled)
    monkeypatch.setattr(default_client, "chat_json", _llm_disabled)
    monkeypatch.setattr(default_client, "chat_schema", _llm_disabled)
