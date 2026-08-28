"""Apply the Dzvonko schema to Supabase via the Management API runSQL endpoint.

Requires a Supabase Personal Access Token (sbp_...) from
https://supabase.com/dashboard/account/tokens

Usage:
    SUPABASE_ACCESS_TOKEN=sbp_... python scripts/apply_migration.py

(Or run the SQL file directly in Supabase Dashboard -> SQL Editor.)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

PROJECT_REF = "wzeauydeiddxzcairuxm"
SQL_PATH = Path(__file__).resolve().parents[1] / "supabase" / "migrations" / "0001_schema.sql"


def main() -> int:
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if not token:
        print("ERROR: set SUPABASE_ACCESS_TOKEN (sbp_...) in the environment.")
        return 1

    sql = SQL_PATH.read_text()
    print(f"Applying schema from {SQL_PATH} ({len(sql)} chars) to project {PROJECT_REF}...")

    # To avoid leaking the token in logs, we send it as an auth header.
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Client-Info": "dzvonko-agent/0.1.0",
    }
    url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"

    with httpx.Client(timeout=120) as client:
        # Split into statements so a single failure is easier to pinpoint.
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for i, stmt in enumerate(statements, start=1):
            try:
                resp = client.post(url, headers=headers, json={"query": stmt})
            except httpx.HTTPError as exc:
                print(f"[{i}/{len(statements)}] network error: {exc}")
                return 1
            if resp.status_code >= 300:
                print(f"[{i}/{len(statements)}] FAILED HTTP {resp.status_code}: {resp.text[:300]}")
                return 1
            print(f"[{i}/{len(statements)}] OK  {stmt[:60].replace(chr(10), ' ')}")

    print("\nSchema applied successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
