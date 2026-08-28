"""Upstash Redis integration for Dzvonko.

Used for lightweight caching, session state and rate-limiting keys.
HTTP REST via `httpx` avoids extra TLS/socket deps in serverless containers.
"""
from __future__ import annotations

import httpx

from app.config import settings


class UpstashRedis:
    """Minimal Upstash Redis REST client."""

    def __init__(self, url: str | None = None, token: str | None = None) -> None:
        self.url = (url if url is not None else settings.upstash_redis_url or "").rstrip("/")
        self.token = token if token is not None else settings.upstash_redis_token or ""

    @property
    def configured(self) -> bool:
        return bool(self.url and self.token)

    async def _call(self, command: str, *args: str) -> dict:
        if not self.configured:
            raise RuntimeError("Upstash Redis not configured")
        path = "/".join([command, *[str(a) for a in args]])
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.url}/{path}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def ping(self) -> bool:
        try:
            result = await self._call("PING")
            return result.get("result") == "PONG" if isinstance(result, dict) else bool(result)
        except Exception:  # noqa: BLE001
            return False

    async def get(self, key: str) -> str | None:
        data = await self._call("GET", key)
        return data.get("result") if isinstance(data, dict) else None

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        args = [key, value]
        if ex:
            args.extend(["EX", str(ex)])
        data = await self._call("SET", *args)
        return (data.get("result") if isinstance(data, dict) else None) == "OK"

    async def delete(self, key: str) -> int:
        data = await self._call("DEL", key)
        return data.get("result", 0) if isinstance(data, dict) else 0


async def get_redis() -> UpstashRedis:
    return UpstashRedis()
