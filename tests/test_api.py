"""Every endpoint returns valid JSON with the documented shape (WORKFLOW.md step 5)."""
from __future__ import annotations


def first_alert(client, **params):
    r = client.get("/alerts", params={"limit": 1, **params})
    assert r.status_code == 200
    return r.json()["items"][0]


def test_health_and_meta(client):
    assert client.get("/health").json() == {"status": "ok"}
    m = client.get("/meta").json()
    assert m["synthetic"] is True and m["alert_min_score"] == 40
    assert client.get("/health").headers["X-Data-Source"] == "synthetic"


def test_alert_queue_is_ranked_and_filterable(client):
    body = client.get("/alerts", params={"limit": 1000}).json()
    scores = [a["score"] for a in body["items"]]
    assert body["total"] == len(scores) and scores == sorted(scores, reverse=True)
    for team in ["AML", "Fraud", "Safer Gambling"]:
        items = client.get("/alerts", params={"team": team, "limit": 1000}).json()["items"]
        assert all(a["team"] == team for a in items)
    items = client.get("/alerts", params={"type": "location_anomaly", "band": "Critical,High"}).json()["items"]
    assert all("location_anomaly" in a["anomaly_types"] and a["band"] in ("Critical", "High") for a in items)
    assert client.get("/alerts", params={"sort": "bogus"}).status_code == 400


def test_alert_detail(client):
    a = first_alert(client)
    d = client.get(f"/alerts/{a['alert_id']}").json()
    assert d["reasons"] and d["recommended_action"]["action"]
    assert {"peer_median", "own_baseline"} <= set(d["reasons"][0]["comparison"])
    assert client.get("/alerts/A-NOPE").status_code == 404


def test_player_endpoints(client):
    a = first_alert(client)
    pid = a["player_id"]
    p = client.get(f"/players/{pid}").json()
    assert p["alert_id"] == a["alert_id"] and p["recent_transactions"]
    peers = client.get(f"/players/{pid}/peers").json()
    assert len(peers["features"]) == 6 and all("peer_median" in f for f in peers["features"])
    tl = client.get(f"/players/{pid}/timeline").json()
    assert tl["weeks"] and {"baseline", "current"} & {w["window"] for w in tl["weeks"]}
    tx = client.get(f"/players/{pid}/transactions", params={"type": "deposit", "limit": 5}).json()
    assert all(t["type"] == "deposit" for t in tx["items"])
    assert client.get("/players/NOPE").status_code == 404


def test_network_finds_rings(client):
    clusters = client.get("/network/clusters").json()
    assert clusters and clusters[0]["opposite_bets"] > 0
    pid = clusters[0]["players"][0]
    net = client.get(f"/players/{pid}/network").json()
    assert net["cluster_size"] >= 3 and net["edges"]
    assert any(n["is_focus"] for n in net["nodes"])


def test_decision_flow(client):
    a = first_alert(client, status="open")
    aid = a["alert_id"]
    assert client.post(f"/alerts/{aid}/decision", json={"decision": "close"}).status_code == 422
    assert client.post(f"/alerts/{aid}/decision", json={"decision": "maybe"}).status_code == 422
    r = client.post(f"/alerts/{aid}/decision", json={"decision": "escalate", "note": "test", "investigator": "pytest"})
    assert r.status_code == 201 and r.json()["status"] == "escalated"
    assert client.get(f"/alerts/{aid}").json()["status"] == "escalated"
    assert aid in [x["alert_id"] for x in client.get("/alerts", params={"status": "escalated", "limit": 1000}).json()["items"]]
    hist = client.get(f"/alerts/{aid}/decisions").json()
    assert hist[-1]["investigator"] == "pytest"
    assert "escalate" in client.get(f"/alerts/{aid}/report").text


def test_stats_validation_export(client):
    s = client.get("/stats").json()
    assert s["alerts"] == sum(s["by_band"].values()) == sum(s["by_status"].values())
    assert sum(h["players"] for h in s["score_histogram"]) == s["players"]
    assert "recall_by_scenario" in client.get("/validation").json()
    csv = client.get("/alerts/export.csv")
    assert csv.status_code == 200 and csv.text.startswith("rank,alert_id")
