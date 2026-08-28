"""API smoke tests using Starlette's TestClient."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["agent"] == "Dzvonko"


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "docs" in resp.json()


def test_run_graph_health(client):
    resp = client.get("/runs/health")
    assert resp.status_code == 200
    assert resp.json()["graph"] == "ok"


def test_run_workflow_without_profile(client):
    # Full workflow with no profile must not crash and must not submit.
    resp = client.post("/runs", json={"user_id": "u1", "source": "custom"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("submission_status") in (None, "")
