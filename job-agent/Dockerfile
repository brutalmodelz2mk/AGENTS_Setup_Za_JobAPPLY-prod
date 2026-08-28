# Dzvonko — LangGraph job-application automation agent (spec §12)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (minimal) needed for Playwright + health checks
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install the Chromium browser for Playwright (Phase 5). Tolerate failure so the
# core app can still boot if the browser layer is not needed yet.
RUN playwright install chromium --with-deps || true

COPY . .

# Run as a non-root user (spec §12)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
