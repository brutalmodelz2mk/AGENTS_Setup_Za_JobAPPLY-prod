"""FastAPI application entrypoint (spec §23 Phase 1).

Run locally:  uvicorn app.main:app --reload --port 8080
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import AGENT_NAME, __version__
from app.api.routes import health, jobs, profiles, runs
from app.config import settings
from app.llm.openrouter import default_client

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("dzvonko.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s (%s)", AGENT_NAME, __version__, settings.environment)
    logger.info("LLM configured: %s", settings.is_llm_configured)
    yield
    # Graceful resource cleanup on shutdown.
    try:
        await default_client.aclose()
    except Exception:  # noqa: BLE001
        logger.warning("Could not close LLM client cleanly")
    logger.info("Shut down %s", AGENT_NAME)


app = FastAPI(
    title=f"{AGENT_NAME} — Job Application Agent",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(runs.router)
app.include_router(jobs.router)
app.include_router(profiles.router)


@app.get("/")
async def root() -> dict:
    return {
        "agent": AGENT_NAME,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
