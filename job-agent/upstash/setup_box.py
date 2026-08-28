#!/usr/bin/env python3
"""Dzvonko — Upstash Box provisioning (Infrastructure-as-Code).

Creates a fully-configured Upstash Box with every segment wired and verifies
each one communicates. Re-runnable; the box is recreated on each run.

Required env: UPSTASH_BOX_API_KEY (box_... key), GITHUB_PAT,
  SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY,
  OPENROUTER_API_KEY.
"""
from __future__ import annotations

import os
import sys
import time

BOX_NAME = os.environ.get("DZVONKO_BOX_NAME", "dzvonko-agent")
RUNTIME = os.environ.get("DZVONKO_BOX_RUNTIME", "python")
SIZE = os.environ.get("DZVONKO_BOX_SIZE", "medium")
MODEL = os.environ.get("DZVONKO_BOX_MODEL", "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free")


def check(label: str, fn) -> None:
    try:
        print(f"[OK ] {label}: {fn()}")
    except Exception as exc:  # noqa: BLE001
        print(f"[ERR] {label}: {type(exc).__name__}: {str(exc)[:150]}")


def main() -> int:
    api = os.environ.get("UPSTASH_BOX_API_KEY", "")
    if not api:
        print("ERROR: set UPSTASH_BOX_API_KEY")
        return 1

    from upstash_box import Box

    b = Box.create(
        api_key=api,
        name=BOX_NAME,
        runtime=RUNTIME,
        size=SIZE,
        browser=True,           # headless Chromium segment
        keep_alive=False,       # free tier; set True + paid plan for persistence
        labels=["dzvonko"],
        network_policy={"mode": "allow-all"},
        env={},                 # injected at runtime (create-time env is not listed)
        git={
            "token": os.environ.get("GITHUB_PAT", ""),
            "userName": "brutalmodelz2mk",
            "userEmail": "brutalmodelz2mk@users.noreply.github.com",
        },
        agent={"harness": "opencode", "model": MODEL,
               "api_key": os.environ.get("OPENROUTER_API_KEY", "")},
        skills=["upstash/box"],
    )
    bid = b.id
    print("BOX id:", bid)

    # Runtime env injection
    b.set_all_env({
        "SUPABASE_URL": os.environ.get("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_ROLE_KEY": os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        "SUPABASE_ANON_KEY": os.environ.get("SUPABASE_ANON_KEY", ""),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "OPCODE_ZEN_API_KEY1": os.environ.get("OPCODE_ZEN_API_KEY1", ""),
    })
    check("env.inject", lambda: ",".join(b.list_env() or []))

    # Live HTTP server on 8080 so the public URL answers
    def serve() -> str:
        r = b.exec.command(
            'bash -lc "mkdir -p ~/www && echo \'<h1>Dzvonko Upstash Box is LIVE</h1>'
            f'<p>id={bid}</p>\' > ~/www/index.html; '
            '(python3 -m http.server 8080 --directory ~/www > /tmp/http.log 2>&1 &); '
            'sleep 2; echo SERVED"'
        )
        return (r.stdout or r.stderr or "").strip()
    check("http.server", serve)

    check("exec", lambda: b.exec.command('bash -lc "python3 --version"').stdout.strip())
    check("files", lambda: (b.files.write(path="/tmp/x.txt", content="dzvonko"),
                            b.files.read(path="/tmp/x.txt"))[1])
    check(
        "git.identity",
        lambda: b.exec.command(
            'bash -lc "git config --global user.name brutalmodelz2mk; '
            'git config --global user.name"').stdout.strip(),
    )
    check("browser.cdp", lambda: b.browser.cdp_url())
    check("skills", lambda: ",".join(b.skills.list()[:6]))
    check("public.url", lambda: str(b.get_public_url(8080)))

    # Agent -> LLM (note: free-tier models are latency-bound)
    def agent() -> str:
        t = time.time()
        run = b.agent.run(prompt="Reply with exactly: BOX_AGENT_OK", timeout=60)
        out = getattr(run, "output", None) or getattr(run, "result", None)
        return f"{round(time.time() - t, 1)}s -> {str(out)[:80]}"
    check("agent.run", agent)

    print("\nLIVE_URL:", b.get_public_url(8080).url)
    print("BOX_ID:", bid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
