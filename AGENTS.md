# AGENTS.md — LangGraph Job Application Automation Agent

## 1. Project Goal

Build a modular AI job-application assistant using **LangGraph + Python + FastAPI**, with:

- Job discovery and filtering
- Job-page analysis
- Job/application data extraction
- CV and cover-letter preparation
- Browser-assisted application workflow using Playwright
- Email preparation/sending through an authorized email API
- Persistent storage in Supabase/PostgreSQL
- Optional Redis layer later
- LLM access through OpenRouter
- Dockerized deployment on Google Cloud Run

### Important platform rule

The system must not bypass CAPTCHAs, MFA, anti-bot protections, access controls, or other security mechanisms.

For LinkedIn or another platform, prefer official APIs/integrations where available. Browser automation should only be used where permitted by the target site's terms and with the user's authorization.

For final submission of an application, use a **human-in-the-loop confirmation** by default unless the target platform explicitly permits the required automation.

---

## 2. Recommended Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Agent orchestration | LangGraph |
| LLM gateway | OpenRouter |
| API | FastAPI |
| Browser automation | Playwright |
| Database | Supabase PostgreSQL |
| Cache / queue | Optional Redis / Upstash |
| Container | Docker |
| Cloud runtime | Google Cloud Run |
| Scheduling | Cloud Scheduler |
| Secrets | Google Secret Manager |
| Source control | GitHub |
| CI/CD | GitHub Actions or Google Cloud Build |

---

## 3. High-Level Architecture

```text
                         ┌─────────────────────┐
                         │      Frontend       │
                         │ Dashboard / Web UI  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │ API + Auth + Jobs   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      LangGraph      │
                         │   Agent Workflow    │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             ▼                      ▼                      ▼
      Job Discovery           Job Analysis          Application
        Node/Agent              Node/Agent          Preparation
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    ▼
                              OpenRouter
                                    │
                                    ▼
                             Selected LLM
                                    │
             ┌──────────────────────┼──────────────────────┐
             ▼                      ▼                      ▼
          Supabase               Playwright            Email API
          PostgreSQL             Browser               Gmail/etc.
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    ▼
                            Google Cloud Run
```

---

## 4. LangGraph Workflow

Recommended graph:

```text
START
  │
  ▼
load_user_profile
  │
  ▼
discover_jobs
  │
  ▼
deduplicate_jobs
  │
  ▼
analyze_job
  │
  ▼
score_job
  │
  ├── score too low ───────► END
  │
  ▼
prepare_application
  │
  ▼
human_review
  │
  ├── rejected ────────────► END
  │
  ▼
open_application
  │
  ▼
fill_application
  │
  ▼
validate_application
  │
  ├── validation failed ──► retry / human review
  │
  ▼
human_confirm_submit
  │
  ├── cancelled ──────────► END
  │
  ▼
submit_application
  │
  ▼
record_result
  │
  ▼
send_followup_if_enabled
  │
  ▼
END
```

---

## 5. Agent Responsibilities

### Job Discovery

Responsibilities:

- Search configured job sources
- Apply location, role, salary and remote filters
- Normalize job records
- Store source URL
- Avoid duplicate jobs

Never fabricate job listings.

### Job Analysis

Extract:

- Job title
- Company
- Location
- Remote/hybrid/on-site
- Salary when available
- Required skills
- Preferred skills
- Experience requirements
- Education requirements
- Employment type
- Application URL
- Job description

If information is unavailable, use `null`, not a guessed value.

### Job Scoring

Return structured JSON:

```json
{
  "score": 0,
  "match_level": "low|medium|high",
  "reasons": [],
  "missing_requirements": [],
  "recommended": true
}
```

The scoring system must be deterministic enough to explain why a job was recommended.

### Application Preparation

Generate:

- Tailored CV suggestions
- Cover letter
- Answers to application questions
- Structured application data

Never invent:

- Employment history
- Education
- Certifications
- Skills
- Employers
- Dates
- Achievements

User-provided facts are the source of truth.

### Browser Agent

Use Playwright for permitted browser workflows.

Rules:

- Use stable selectors
- Prefer accessible roles/labels
- Wait for actual page state
- Never rely on arbitrary sleep as the primary synchronization method
- Capture screenshots on failure
- Save useful diagnostic logs
- Detect CAPTCHA/MFA and stop
- Never attempt to bypass security controls
- Require confirmation before final submission by default

---

## 6. LangGraph State

Use a typed state model.

Example:

```python
from typing import TypedDict, Any

class AgentState(TypedDict, total=False):
    user_id: str
    search_query: str
    jobs: list[dict[str, Any]]
    selected_job: dict[str, Any] | None
    job_analysis: dict[str, Any] | None
    match_score: float
    application_data: dict[str, Any] | None
    browser_status: str
    human_approved: bool
    submission_status: str
    error: str | None
```

Keep state small and serializable.

Do not put passwords, API keys, cookies, or sensitive browser credentials into LangGraph state.

---

## 7. OpenRouter Configuration

Use environment variables.

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=your_selected_model
```

Never commit `.env`.

Use different models for different workloads if useful:

```env
MODEL_FAST=your_fast_model
MODEL_REASONING=your_reasoning_model
MODEL_EXTRACTION=your_extraction_model
```

The application should not hard-code provider credentials.

---

## 8. Supabase Configuration

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

The service-role key must only be used server-side.

Recommended tables:

```text
users
user_profiles
job_sources
jobs
job_matches
applications
application_events
agent_runs
email_messages
```

Minimum `jobs` fields:

```text
id
source
external_id
title
company
location
url
description
salary_min
salary_max
employment_type
remote_type
posted_at
created_at
```

Minimum `applications` fields:

```text
id
user_id
job_id
status
application_url
match_score
cover_letter
submitted_at
created_at
updated_at
```

---

## 9. Redis — Optional

Redis is NOT required for version 1.

Start with:

```text
LangGraph
FastAPI
Supabase
OpenRouter
Playwright
Cloud Run
```

Add Redis later for:

- Background job queues
- Rate limiting
- Distributed locks
- Short-lived caching
- Job status
- Concurrent workers

Possible configuration:

```env
REDIS_URL=redis://...
```

Do not introduce Redis unless there is a measurable need.

---

## 10. Email

Use an authorized email provider/API.

Recommended architecture:

```text
Agent
  │
  ▼
prepare email
  │
  ▼
human approval
  │
  ▼
email provider API
  │
  ▼
send
  │
  ▼
store event in Supabase
```

Never store an email provider password in source code.

Use OAuth/API credentials through Secret Manager.

---

## 11. Project Structure

```text
job-agent/
│
├── app/
│   ├── api/
│   │   ├── routes/
│   │   └── dependencies.py
│   │
│   ├── agents/
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── nodes/
│   │       ├── discovery.py
│   │       ├── analysis.py
│   │       ├── scoring.py
│   │       ├── application.py
│   │       ├── browser.py
│   │       └── email.py
│   │
│   ├── browser/
│   │   ├── playwright_client.py
│   │   └── selectors.py
│   │
│   ├── database/
│   │   ├── supabase.py
│   │   └── repositories/
│   │
│   ├── llm/
│   │   └── openrouter.py
│   │
│   ├── models/
│   ├── services/
│   ├── config.py
│   └── main.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── AGENTS.md
└── README.md
```

---

## 12. Docker

Use a production-ready Python image.

The container must:

- Run as a non-root user where practical
- Expose the configured application port
- Read configuration from environment variables
- Write logs to stdout/stderr
- Avoid storing persistent application data locally

For Playwright, install only the required browser dependencies.

---

## 13. Google Cloud Run

Target architecture:

```text
GitHub
   │
   ▼
CI/CD
   │
   ▼
Container Registry / Artifact Registry
   │
   ▼
Google Cloud Run
   │
   ├── FastAPI
   ├── LangGraph
   └── Playwright worker when appropriate
         │
         ├── Supabase
         ├── OpenRouter
         └── Email API
```

Recommended environment:

```env
PORT=8080
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Cloud Run should remain stateless.

Persistent data belongs in Supabase.

Secrets belong in Google Secret Manager or another managed secret system.

---

## 14. Scheduled Job Discovery

For periodic discovery:

```text
Cloud Scheduler
      │
      ▼
Cloud Run endpoint
      │
      ▼
LangGraph workflow
      │
      ▼
discover → analyze → score → store
```

Do not run an infinite background loop inside a Cloud Run request container.

For long-running workloads, split work into jobs/tasks and persist their status.

---

## 15. Error Handling

Every node must handle recoverable and fatal errors.

Recommended pattern:

```python
try:
    result = operation()
except TemporaryError:
    retry()
except ValidationError:
    request_human_review()
except Exception as exc:
    log_error(exc)
    save_failed_run()
```

Retry only transient failures.

Use exponential backoff.

Never blindly retry:

- Authentication failures
- Invalid credentials
- CAPTCHA
- MFA
- Permission errors
- Policy/security blocks

---

## 16. Browser Automation Rules

Prefer:

```python
page.get_by_role(...)
page.get_by_label(...)
page.locator(...)
```

Avoid fragile selectors such as:

```text
div:nth-child(17)
```

Use:

```text
timeout
retry
screenshot
HTML diagnostics
structured logging
```

When an unexpected security challenge appears:

```text
STOP
↓
save diagnostic state
↓
notify user
↓
wait for human action
```

Never bypass the challenge.

---

## 17. Observability

Every agent run should have:

```text
run_id
user_id
workflow
node
started_at
finished_at
duration_ms
status
error
```

Log structured JSON where practical.

Example:

```json
{
  "run_id": "abc123",
  "node": "analyze_job",
  "status": "success",
  "duration_ms": 842
}
```

Never log:

- API keys
- Passwords
- OAuth tokens
- Session cookies
- Full authentication headers

---

## 18. Security

Required:

- `.env` in `.gitignore`
- Secrets stored outside source control
- Input validation
- Authentication and authorization
- Rate limiting
- Secure cookies/tokens
- Least-privilege database access
- HTTPS
- Dependency updates
- Audit logging for application submissions

Never expose:

```text
OPENROUTER_API_KEY
SUPABASE_SERVICE_ROLE_KEY
email credentials
browser session cookies
```

to the frontend.

---

## 19. Human-in-the-Loop

The default application workflow must be:

```text
Job found
   ↓
Job analyzed
   ↓
Application prepared
   ↓
User reviews
   ↓
User approves
   ↓
Browser fills form
   ↓
User confirms final submission
   ↓
Application submitted
```

The agent must never silently submit an application unless the exact workflow is authorized and permitted by the target service.

---

## 20. Testing Strategy

### Unit Tests

Test:

- Job parsing
- Deduplication
- Scoring
- State transitions
- Prompt output validation
- Database repositories

### Integration Tests

Test:

- OpenRouter connection
- Supabase connection
- Email provider
- LangGraph workflow

Use mocks for external services where possible.

### Browser Tests

Use a controlled test website or local mock application form.

Do not use production job websites as an automated test environment.

---

## 21. Coding Rules for Codex / OpenCode

1. Inspect the existing project before changing files.
2. Do not rewrite working modules unnecessarily.
3. Keep modules small and focused.
4. Use type hints.
5. Use Pydantic for API/input validation.
6. Use async code where it provides a real benefit.
7. Never hard-code credentials.
8. Never invent APIs.
9. Never invent selectors.
10. Never invent user information.
11. Add tests for non-trivial logic.
12. Preserve existing functionality unless intentionally changing it.
13. Prefer explicit errors over silent fallback.
14. Keep external integrations behind service interfaces.
15. Make LLM outputs structured and validated.
16. Keep browser automation isolated from business logic.
17. Keep database access isolated from agent nodes.
18. Use dependency injection where practical.
19. Add logging around external calls.
20. Document architectural changes.

---

## 22. Definition of Done

A feature is complete only when:

- Code is implemented
- Configuration is documented
- Environment variables are documented
- Tests are added
- Errors are handled
- Logs are useful
- Secrets are protected
- Docker build succeeds
- Local execution succeeds
- Cloud Run deployment succeeds
- Supabase integration works
- OpenRouter integration works
- Human approval works where required
- README is updated

---

## 23. Initial Build Order

Build in this order:

### Phase 1 — Foundation

1. Create Python project
2. Create virtual environment
3. Install LangGraph
4. Install FastAPI
5. Configure Pydantic settings
6. Configure OpenRouter
7. Create basic LangGraph state
8. Create health endpoint

### Phase 2 — Database

1. Create Supabase project
2. Create schema
3. Add repository layer
4. Add job storage
5. Add application storage
6. Add agent-run logging

### Phase 3 — Job Pipeline

1. Job discovery
2. Normalization
3. Deduplication
4. Job analysis
5. Match scoring
6. Database persistence

### Phase 4 — Application Preparation

1. User profile
2. CV data
3. Cover letter generation
4. Application-question generation
5. Human review UI/API

### Phase 5 — Browser

1. Playwright service
2. Controlled test form
3. Field mapping
4. Validation
5. Screenshot/error handling
6. Human confirmation before submission

### Phase 6 — Email

1. Provider integration
2. Draft generation
3. Human approval
4. Send
5. Record event

### Phase 7 — Cloud

1. Dockerize
2. Build image
3. Push to Artifact Registry
4. Deploy to Cloud Run
5. Configure Secret Manager
6. Configure Cloud Scheduler
7. Add monitoring/logging

### Phase 8 — Optimization

Only after the MVP works:

- Add Redis
- Add background queues
- Add concurrency
- Add caching
- Add multiple workers
- Add advanced observability

---

## 24. MVP Architecture

The first version should deliberately remain simple:

```text
                OpenRouter
                    │
                    ▼
Supabase ◄── FastAPI + LangGraph ──► Playwright
                    │
                    ▼
               Cloud Run
```

No Redis initially.

No unnecessary microservices.

No unnecessary multi-agent complexity.

Build a reliable single LangGraph workflow first, then split components only when performance or maintainability requires it.

---

## 25. Primary Objective

The priority is:

**Reliable > Fast > Complex**

Build the smallest working system first.

Every automation step must be:

- observable
- recoverable
- testable
- authorized
- explainable

The agent should assist the user rather than operate as an uncontrolled autonomous browser bot.
