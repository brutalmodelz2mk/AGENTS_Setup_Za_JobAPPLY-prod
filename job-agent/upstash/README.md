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

- **Free tier** limits: 10 concurrent boxes, 2 CPU / 4 GB / 5 GB storage, 5 CPU
  hours/month, **1-hour idle timeout**, then the box shuts down. `keep_alive`
  and `init_command` are disabled on the free tier.
- For a persistent box + auto-restart init script
  (`hermes gateway start > gateway.log 2>&1 &`), add a payment method at
  https://console.upstash.com → Billing and set `keep_alive=True`.
- **Agent LLM**: the OpenCode harness is installed and picks up `OPENROUTER_API_KEY`.
  The verification uses `opencode run -m openrouter/<model>` executed inside the
  box (the SDK's `box.agent.run()` stream can time out on free-tier latency).
- The box key `box_...` is used to create/list boxes; the account API key is for
  the Upstash REST/developer API.

## Live test

```bash
curl https://<box-id>-8080.preview.box.upstash.com/
# expected: <h1>Dzvonko Upstash Box is LIVE</h1><p>id=<box-id></p>
```
