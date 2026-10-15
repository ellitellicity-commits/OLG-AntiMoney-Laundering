"""Jube integration: payload mapping, decision mapping, and a full push/pull round trip against the mock Jube."""
from __future__ import annotations

import re
import socket
import threading
import time

import pytest
import uvicorn

from backend.integrations import jube, jube_mock

MY_ALERT = {  # shape produced by backend/pipeline/detect.py
    "alert_id": "A-P00066", "player_id": "P00066", "score": 92, "band": "Critical", "team": "AML",
    "anomaly_types": ["income_mismatch", "cash_cycling"], "created_at": "2026-10-01",
    "reasons": [{"code": "INCOME_MISMATCH", "anomaly_type": "income_mismatch", "title": "Deposits exceed declared income",
                 "detail": "Deposited $5,370 in the last 30 days.", "evidence": {"deposits_30d": 5370}, "points": 40}],
    "recommended_action": {"action": "Request source-of-funds documentation", "team": "AML", "rationale": "x"},
    "key_metrics": {"deposits_30d": 5370.0, "withdrawals_30d": 4100.0, "net_loss_30d": 300.0},
    "profile": {"income_band": "20-40k", "occupation": "Retail associate", "home_region": "Northern Ontario"},
}
CONTRACT_ALERT = {  # shape from docs/API_CONTRACT.md on the frontend-mock branch
    "player_id": "P-20917", "risk_score": 84, "band": "high", "anomaly_types": ["location"],
    "reasons": [{"type": "location", "headline": "Bets placed from Malta on an Ontario account",
                 "evidence": "62% of sessions from Malta in 30 days.", "weight": 40}],
    "recommended_action": {"label": "Verify account owner", "team": "Fraud", "rationale": "y"},
}
LOW_ALERT = {**MY_ALERT, "alert_id": "A-P00001", "player_id": "P00001", "score": 45, "band": "Medium"}


def test_normalise_accepts_both_shapes():
    a = jube.normalise_alert(MY_ALERT)
    assert (a["player_id"], a["score"], a["action"], a["reasons"][0]["points"]) == \
           ("P00066", 92, "Request source-of-funds documentation", 40)
    b = jube.normalise_alert(CONTRACT_ALERT)
    assert (b["player_id"], b["alert_id"], b["score"], b["team"]) == ("P-20917", "A-P-20917", 84, "Fraud")
    assert b["reasons"][0]["title"].startswith("Bets placed") and b["reasons"][0]["detail"].startswith("62%")
    assert b["reasons"][0]["points"] == 40


def test_payload_has_every_configured_field():
    p = jube.alert_to_payload(MY_ALERT)
    for name, xpath, _, _ in jube.JUBE_FIELDS:
        assert xpath == f"$.{name}" and name in p
    assert p["RiskScore"] == 92 and p["CurrencyAmount"] == 5370.0 and p["Reasons"][0]["Code"] == "INCOME_MISMATCH"
    # .NET round-trip format with 7 fractional digits and an offset
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{7}[+-]\d\d:\d\d", p["TxnDateTime"])


@pytest.mark.parametrize("case,expected", [
    ({"Id": 1, "ClosedStatusId": 3, "CaseWorkflowStatusName": "Closed"}, "close"),
    ({"Id": 1, "ClosedStatusId": 0, "CaseWorkflowStatusName": "Escalated"}, "escalate"),
    ({"Id": 1, "ClosedStatusId": 0, "CaseWorkflowStatusName": "In Review"}, "accept"),
    ({"Id": 1, "ClosedStatusId": 0, "CaseWorkflowStatusName": "Open", "Locked": True}, "accept"),
    ({"Id": 1, "ClosedStatusId": 0, "CaseWorkflowStatusName": "Open"}, None),
])
def test_case_to_decision(case, expected):
    d = jube.case_to_decision(case)
    assert (d["decision"] if d else None) == expected


@pytest.fixture(scope="module")
def mock_jube():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(jube_mock.app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    t.join(timeout=5)


@pytest.fixture
def client(mock_jube, monkeypatch, tmp_path):
    jube_mock.reset()
    monkeypatch.setattr(jube_mock, "API_KEY", "test-key")
    monkeypatch.setenv("JUBE_STATE_PATH", str(tmp_path / "jube_sync.json"))
    cfg = jube.JubeConfig(url=mock_jube, model_guid=jube_mock.MODEL_GUID, api_key="test-key", min_score=70)
    return jube.JubeClient(cfg)


def test_round_trip(client):
    st = jube.status(client)
    assert st["reachable"] and st["auth"] == "api_key"

    res = jube.push_alerts([MY_ALERT, CONTRACT_ALERT, LOW_ALERT], client)
    assert [r["status"] for r in res] == ["sent", "sent"]  # the 45-score alert is below the threshold
    assert res[0]["response"]["Activation"]["OLGRiskScoreCase"]["CaseId"] == 1
    assert [r["status"] for r in jube.push_alerts([MY_ALERT], client)] == ["skipped"]  # same score: no resend

    recorded = {}
    pull = jube.pull_decisions([MY_ALERT, CONTRACT_ALERT], client, record=lambda aid, d: recorded.update({aid: d}))
    assert {r["status"] for r in pull} == {"open_in_jube"} and not recorded

    # investigator works the cases inside Jube
    jube_mock.set_status(1, "Escalated", user="analyst.a")
    jube_mock.set_status(2, "Closed", user="analyst.b")
    pull = jube.pull_decisions([MY_ALERT, CONTRACT_ALERT], client, record=lambda aid, d: recorded.update({aid: d}))
    assert recorded["A-P00066"]["decision"] == "escalate" and recorded["A-P00066"]["investigator"] == "analyst.a"
    assert recorded["A-P-20917"]["decision"] == "close"
    # pulling again does not re-record unchanged cases
    again = jube.pull_decisions([MY_ALERT, CONTRACT_ALERT], client, record=lambda aid, d: pytest.fail("re-recorded"))
    assert {r["status"] for r in again} == {"unchanged"}


def test_bad_key_and_model_are_reported(client, mock_jube):
    bad = jube.JubeClient(jube.JubeConfig(url=mock_jube, model_guid=jube_mock.MODEL_GUID, api_key="wrong"))
    res = jube.push_alerts([MY_ALERT], bad)
    assert res[0]["status"] == "error" and "HTTP 401" in res[0]["detail"]
    wrong_model = jube.JubeClient(jube.JubeConfig(url=mock_jube, model_guid="nope", api_key="test-key"))
    assert "JUBE_MODEL_GUID" in jube.push_alerts([MY_ALERT], wrong_model)[0]["detail"]


def test_unreachable_jube_stops_early(tmp_path, monkeypatch):
    monkeypatch.setenv("JUBE_STATE_PATH", str(tmp_path / "s.json"))
    c = jube.JubeClient(jube.JubeConfig(url="http://127.0.0.1:9", model_guid="x", timeout=1))
    res = jube.push_alerts([MY_ALERT, CONTRACT_ALERT], c)
    assert len(res) == 1 and "Cannot reach Jube" in res[0]["detail"]


def test_router_against_mock(client, mock_jube, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.integrations.jube_router import make_jube_router

    decisions = []
    app = FastAPI()
    app.include_router(make_jube_router(lambda: [MY_ALERT, LOW_ALERT], lambda aid, d: decisions.append((aid, d)),
                                        client_factory=lambda: client))
    with TestClient(app) as tc:
        assert tc.post("/jube/push", params={"dry_run": True}).json()["summary"] == {"dry_run": 1}
        assert tc.post("/jube/push").json()["summary"] == {"sent": 1}
        jube_mock.set_status(1, "In Review")
        assert tc.post("/jube/pull").json()["summary"] == {"recorded": 1}
        assert decisions[0][0] == "A-P00066" and decisions[0][1]["decision"] == "accept"
        assert tc.get("/jube/spec").json()["activation_rule"]["case_key"] == "PlayerId"
    unconfigured = FastAPI()
    unconfigured.include_router(make_jube_router(lambda: [], client_factory=lambda: jube.JubeClient(jube.JubeConfig())))
    with TestClient(unconfigured) as tc:
        assert tc.post("/jube/push").status_code == 503
