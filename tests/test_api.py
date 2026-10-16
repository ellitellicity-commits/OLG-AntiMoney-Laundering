"""Every endpoint the dashboard uses returns valid JSON with the documented shape (WORKFLOW.md step 5).

Runs against the small temp dataset from conftest.py. The API's data paths are pointed at it for this module
only, and decisions and notes are written there, never to data/.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def client(data_dir):
    from fastapi.testclient import TestClient

    from backend.app import ai, main
    from backend.pipeline import common

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("LLM_PROVIDER", "none")
        for name, sub in [("DATA", ""), ("SYNTH", "synthetic"), ("FEATURES", "features"), ("SCORES", "scores"),
                          ("MODELS", "models")]:
            mp.setattr(main, name, data_dir / sub if sub else data_dir, raising=False)
            mp.setattr(common, name, data_dir / sub if sub else data_dir)
        mp.setattr(main, "DECISIONS_FILE", data_dir / "decisions.json")
        mp.setattr(main, "NOTES_FILE", data_dir / "notes.json")
        mp.setattr(ai, "CACHE_FILE", data_dir / "ai_cache.json")
        with TestClient(main.app) as c:
            yield c


def first_alert(client, **params):
    r = client.get("/alerts", params={"limit": 1, **params})
    assert r.status_code == 200
    return r.json()["alerts"][0]


def test_health_and_meta(client):
    assert client.get("/health").json() == {"status": "ok"}
    m = client.get("/meta").json()
    assert m["synthetic"] is True and m["players"] == 1200 and m["alerts"] > 0
    assert m["bands"] == ["Low", "Medium", "High", "Critical"]
    assert m["teams"] == ["AML", "Fraud", "Safer Gambling"]


def test_alert_queue_is_ranked_and_filterable(client):
    body = client.get("/alerts", params={"limit": 5000}).json()
    order = [(a["score"], a["points_total"]) for a in body["alerts"]]
    assert body["total"] == len(order) and order == sorted(order, reverse=True)
    for team in ["AML", "Fraud", "Safer Gambling"]:
        items = client.get("/alerts", params={"team": team, "limit": 5000}).json()["alerts"]
        assert all(a["team"] == team for a in items)
    items = client.get("/alerts", params={"type": "location_anomaly", "band": "Critical"}).json()["alerts"]
    assert all("location_anomaly" in a["anomaly_types"] and a["band"] == "Critical" for a in items)
    assert client.get("/alerts", params={"sort": "bogus"}).status_code == 400


def test_alert_detail(client):
    a = first_alert(client)
    d = client.get(f"/alerts/{a['alert_id']}").json()
    assert d["reasons"] and d["recommended_action"]["action"] and d["confidence"]["level"]
    assert all(r["detail"] and r["evidence"] for r in d["reasons"])
    assert client.get("/alerts/ALR-NOPE").status_code == 404


def test_player_endpoints(client):
    a = first_alert(client)
    pid = a["player_id"]
    p = client.get(f"/players/{pid}").json()
    assert p["alert_id"] == a["alert_id"] and p["transactions"]
    peers = client.get(f"/players/{pid}/peers").json()
    assert len(peers["metrics"]) == 5 and all("median" in m["peer"] for m in peers["metrics"])
    tl = client.get(f"/players/{pid}/timeline").json()
    assert len(tl["weeks"]) == 26 and tl["current_window_start"] > tl["baseline_start"]
    flagged = client.get(f"/players/{pid}", params={"flagged_only": True}).json()["transactions"]
    assert all(t["flags"] for t in flagged)
    assert client.get("/players/NOPE").status_code == 404


def test_network_finds_rings(client):
    ring = first_alert(client, type="linked_players")
    net = client.get(f"/players/{ring['player_id']}/network").json()
    assert net["cluster_size"] >= 3 and net["linked_players"]
    assert all(lp["shared"] for lp in net["linked_players"])


def test_decision_flow(client):
    a = first_alert(client, status="New")
    aid = a["alert_id"]
    assert client.post(f"/alerts/{aid}/decision", json={"decision": "close", "investigator": "pytest"}).status_code == 422
    assert client.post(f"/alerts/{aid}/decision", json={"decision": "maybe"}).status_code == 422
    assert client.post(f"/alerts/{aid}/decision", json={"decision": "escalate"}).status_code == 422
    r = client.post(f"/alerts/{aid}/decision", json={"decision": "escalate", "note": "test", "investigator": "pytest"})
    assert r.status_code == 200 and r.json()["status"] == "Escalated"
    assert client.get(f"/alerts/{aid}").json()["status"] == "Escalated"
    assert aid in [x["alert_id"] for x in client.get("/alerts", params={"status": "Escalated"}).json()["alerts"]]
    trail = client.get("/audit").json()["decisions"]
    assert trail[0]["alert_id"] == aid and trail[0]["investigator"] == "pytest"
    assert "pytest" in client.get("/audit.csv").text
    assert "Escalated" in client.get(f"/alerts/{aid}/report").text


def test_stats_watchlist_model(client):
    s = client.get("/stats").json()
    assert s["alerts"] == sum(s["by_band"].values()) == sum(s["by_status"].values())
    assert s["players"] == 1200
    wl = client.get("/watchlist").json()
    assert wl["total"] == len(wl["alerts"]) and all(a["kind"] == "watchlist" for a in wl["alerts"])
    assert client.get("/model").json()["metrics"]
