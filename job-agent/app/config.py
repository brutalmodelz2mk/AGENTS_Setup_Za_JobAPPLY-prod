"""Application configuration loaded from environment variables (Pydantic Settings)."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated configuration.

    All values come from the process environment or a local `.env` file.
    Never hard-code secrets; the `.env` file is gitignored.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Server ---
    port: int = 8080
    environment: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    # --- OpenRouter ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openrouter/free"
    # Comma-separated spare keys for automatic rotation on 401/429.
    openrouter_keys: str = ""

    model_fast: str = "openrouter/free"
    model_reasoning: str = "openrouter/free"
    model_extraction: str = "openrouter/free"

    @property
    def rotation_keys(self) -> list[str]:
        """Parsed list of backup OpenRouter keys for rotation."""
        return [k.strip() for k in self.openrouter_keys.split(",") if k.strip()]

    # --- Supabase (AGENT_Dzvonko-DB) ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # --- Email (Phase 6, human-approved) ---
    email_provider: str = "smtp"
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_smtp_user: str = ""
    email_smtp_password: str = ""

    # --- Browser (Phase 5) ---
    browser_headless: bool = True
    browser_timeout_ms: int = 15_000

    # --- Branding ---
    agent_name: str = "Dzvonko"
    x_title: str = "Za JobAPPLY"
    http_referer: str = "https://za-jobapply.example"

    @property
    def is_llm_configured(self) -> bool:
        """True only for a real OpenRouter key (rejects placeholders)."""
        key = (self.openrouter_api_key or "").strip()
        if not key or "REPLACE" in key.upper() or "CHANGEME" in key.upper():
            return False
        return key.startswith("sk-")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
