"""Jube round trip through the real API (backend/app/main.py) against the mock Jube.

Needs pipeline outputs in data/ (run .\\run_demo.ps1 or the pipeline scripts first); skipped otherwise.
Decisions are written to a temp file, never to data/decisions.json.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.integrations import jube_mock
from test_jube import mock_jube  # noqa: F401  (module-scoped fixture: mock Jube on a free port)

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "scores" / "alerts.json").exists(),
                                reason="run the pipeline first (data/scores/alerts.json missing)")


@pytest.fixture
def api(mock_jube, monkeypatch, tmp_path):  # noqa: F811
    from fastapi.testclient import TestClient

    from backend.app import main

    jube_mock.reset()
    monkeypatch.setattr(jube_mock, "API_KEY", "")
    monkeypatch.setenv("JUBE_URL", mock_jube)
    monkeypatch.setenv("JUBE_MODEL_GUID", jube_mock.MODEL_GUID)
    monkeypatch.setenv("JUBE_STATE_PATH", str(tmp_path / "jube_sync.json"))
    monkeypatch.setattr(main, "DECISIONS_FILE", tmp_path / "decisions.json")
    with TestClient(main.app) as c:
        saved = main.store.decisions
        main.store.decisions = {}
        yield c
        main.store.decisions = saved


def test_push_and_pull_through_the_api(api):
    st = api.get("/jube/status").json()
    assert st["reachable"] and st["model_guid_set"]

    alerts = api.get("/alerts", params={"min_score": 70, "limit": 5000}).json()["alerts"]
    pushed = api.post("/jube/push").json()
    assert pushed["summary"] == {"sent": len(alerts)}
    cases = api.get("/jube/status").json()["pushed"]
    assert cases == len(alerts)

    # the payload carries the money figures from the features table
    first = jube_mock.DB["events"][0]["payload"]
    assert first["Deposits30d"] > 0 and first["RiskScore"] >= 70 and first["Reasons"]

    case = jube_mock.list_cases()[0]
    alert_id = next(a["alert_id"] for a in alerts if a["player_id"] == case["CaseKeyValue"])
    jube_mock.set_status(case["Id"], "Escalated", user="analyst.a")
    assert api.post("/jube/pull").json()["summary"]["recorded"] == 1

    detail = api.get(f"/alerts/{alert_id}").json()
    assert detail["status"] == "Escalated"
    assert detail["decisions"][-1]["investigator"] == "analyst.a (via Jube)"
    assert any(r["alert_id"] == alert_id for r in api.get("/audit").json()["decisions"])
