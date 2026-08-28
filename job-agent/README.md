# Dzvonko — Job Application Automation Agent

A modular AI agent that discovers, analyzes, scores and (with human approval)
applies to jobs, built with **LangGraph + Python + FastAPI**, backed by
**Supabase** and an **OpenRouter** LLM gateway.

> Spec source: `../AGENTS_Creation_Specification_Docs.md`

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ (3.14 tested) |
| Orchestration | LangGraph |
| LLM gateway | OpenRouter (OpenAI-compatible) |
| API | FastAPI + Uvicorn |
| Browser | Playwright |
| Database | Supabase PostgreSQL (project `AGENT_Dzvonko-DB`) |
| Container | Docker / Google Cloud Run |

## Workflow

```
load_user_profile → discover → deduplicate → analyze → score
  → (recommended?) → prepare_application → human_review
  → open → fill → validate → human_confirm_submit
  → submit → record_result → send_followup → END
```

**Human-in-the-loop:** the agent never submits without explicit approval
(`human_approved`) and final confirmation (`human_confirm_submit`), and it
stops on CAPTCHA/MFA instead of bypassing any security control.

## Layout

```
job-agent/
├── app/
│   ├── api/routes/        # health, runs, jobs, profiles endpoints
│   ├── agents/graph.py    # compiled LangGraph workflow
│   ├── agents/nodes/      # discovery, analysis, scoring, application
│   ├── browser/           # Playwright client + selectors
│   ├── database/          # Supabase client + repositories
│   ├── llm/openrouter.py  # OpenRouter chat + structured JSON helpers
│   ├── models/            # Pydantic domain models
│   ├── config.py          # Pydantic Settings (env-driven)
│   └── main.py            # FastAPI app
├── supabase/migrations/0001_schema.sql
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## Setup

```bash
cd job-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then fill in real secrets
```

Required env (see `.env.example`):

- `OPENROUTER_API_KEY` — an `sk-or-v1-…` key (from your OpenRouter account)
- `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`
- Email + browser options

`api_keys.json`, `AGENTS_SETUP.md`, `.env`, and `*apikey*.txt` are **gitignored**.

## Run locally

```bash
uvicorn app.main:app --reload --port 8080
curl http://127.0.0.1:8080/health
```

Run the whole workflow:

```bash
curl -X POST http://127.0.0.1:8080/runs \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","source":"custom"}'
```

## Database (Phase 2)

Apply the schema to the `AGENT_Dzvonko-DB` project once (any one of):

1. Supabase Dashboard → SQL Editor → paste `supabase/migrations/0001_schema.sql`, or
2. Management API (needs a `sbp_…` token from
   https://supabase.com/dashboard/account/tokens):

   ```bash
   SUPABASE_ACCESS_TOKEN=sbp_... python scripts/apply_migration.py
   ```

Tables: `users`, `user_profiles`, `job_sources`, `jobs`, `job_matches`,
`applications`, `application_events`, `agent_runs`, `email_messages`.

> Note: the hosted Supabase MCP (`mcp.supabase.com`) requires OAuth/sbp_ auth;
> `scripts/apply_migration.py` is the token-based path. `sb_secret…` keys are
> PostgREST keys and cannot run DDL.

## Tests

```bash
python -m pytest -q
```

Covers job normalization/dedup, deterministic scoring, the human-in-the-loop
gate, the compiled graph, and API health.

## Build order vs. spec

- ✅ Phase 1 Foundation (config, state, OpenRouter, FastAPI health)
- ✅ Phase 2 Database (schema, client, repositories)
- ✅ Phase 3 Job pipeline (discovery, analysis, scoring)
- ✅ Phase 4 Application prep (cover letter, fields, human review routes)
- ✅ Phase 5 Browser service (Playwright client, gated submission)
- ✅ Phase 6 Email service (SMTP, human-approved)
- 🔒 Phase 7 Cloud — Dockerfile/compose ready; Cloud Run deploy pending GCP creds
- ⏸️ Phase 8 Optimization — out of scope for MVP per spec

## Notes

- Never fabricated data: missing job/profile fields are `null`, and CV facts
  come from the user profile only.
- OpenRouter keys are redacted in the source docs; set your real one in `.env`.
