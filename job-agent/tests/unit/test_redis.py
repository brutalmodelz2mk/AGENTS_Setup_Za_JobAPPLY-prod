"""Unit tests for Upstash Redis wrapper."""
from __future__ import annotations

import pytest

from app.database.redis import UpstashRedis


@pytest.mark.asyncio
async def test_configured():
    r = UpstashRedis(url="https://example.upstash.io", token="token")
    assert r.configured is True


@pytest.mark.asyncio
async def test_not_configured():
    r = UpstashRedis(url="", token="")
    assert r.configured is False
