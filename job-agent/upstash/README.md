# Upstash Box — Dzvonko segment (v0.1.0)

Upstash Box sandbox for the Dzvonko agent. Proves/scripts the full Box
architecture: agent, exec, files, git, browser, skills, env, network policy and
a live public URL. Re-run `setup_box.py` to recreate + re-verify the box.

## Architecture points (all verified in `setup_box.py`)

| Segment | What it does | How verified |
|---|---|---|
| `agent` | OpenCode harness + OpenRouter LLM | `box.agent.run()` / `opencode run --model ...` |
| `exec` | shell inside the box | `python3 --version` |
| `files` | file I/O | write + read |
| `git` | git identity + ops | `git config`, clone/commit |
| `browser` | headless Chromium + CDP | `box.browser.cdp_url()` |
| `skills` | agent skills (upstash/box + 10) | `box.skills.list()` |
| `env` | injected secrets | `box.list_env()` |
| `network` | egress policy | `allow-all` |
| `public` | live HTTPS endpoint | `/` returns 200 |

## Run

```bash
export UPSTASH_BOX_API_KEY=box_...     # create/list key
export GITHUB_PAT=ghp_...              # for the git segment
export SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... SUPABASE_ANON_KEY=...
export OPENROUTER_API_KEY=sk-or-v1-... # for the agent segment
python setup_box.py
```

## Notes / caveats

- **Free tier** boxes are **ephemeral** (auto-delete after the session) and
  **cannot** use `init_command`/keep-alive. For a persistent box + auto-restart
  init script (`hermes gateway start > gateway.log 2>&1 &`), add a payment
  method at https://console.upstash.com → Billing and set `keep_alive=True`.
- **Agent LLM latency**: free-tier OpenRouter models are congested; the agent
  call may be slow. Prefer a paid/priority model or `openrouter/free`.
- `box.agent.run()` (python-sdk 0.3.0) can hit a 0.1s read-timeout on the
  stream — retrieve agent output via `opencode run` (exec) or the TS SDK if so.
- The box key `box_...` is per-box; the account API key cannot create/list boxes.
