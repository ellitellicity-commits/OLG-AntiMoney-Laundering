"""Pinned AI notes (docs/CHAT_CONTRACT.md 4.8): pin, remove, and where notes show up.

Needs pipeline outputs in data/ (run .\\run_demo.ps1 or the pipeline scripts first); skipped otherwise.
Decisions and notes are written to a temporary folder, never to data/.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "scores" / "alerts.json").exists(),
                                reason="run the pipeline first (data/scores/alerts.json missing)")
NOTE = {"question": "Why is this player High confidence?", "answer": "Six kinds of evidence agree.\nScore 97.",
        "provider": "groq", "model": "openai/gpt-oss-20b", "verified": True, "investigator": " J. Doe "}
NOTE_KEYS = {"note_id", "alert_id", "question", "answer", "provider", "model", "verified", "investigator",
             "recorded_at"}


@pytest.fixture
def api(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from backend.app import main
    monkeypatch.setattr(main, "DECISIONS_FILE", tmp_path / "decisions.json")
    monkeypatch.setattr(main, "NOTES_FILE", tmp_path / "notes.json")
    with TestClient(main.app) as c:
        c.notes_file = tmp_path / "notes.json"
        yield c


def test_pin_shows_in_alert_and_does_not_change_status(api):
    before = api.get("/alerts/ALR-00405").json()
    r = api.post("/alerts/ALR-00405/notes", json=NOTE)
    assert r.status_code == 201, r.text
    note = r.json()
    assert set(note) == NOTE_KEYS and note["note_id"] == "N-0001" and note["investigator"] == "J. Doe"
    after = api.get("/alerts/ALR-00405").json()
    assert after["notes"] == [note]
    assert (after["status"], after["team"], after["decisions"]) == (before["status"], before["team"], before["decisions"])
    assert api.post("/alerts/ALR-00850/notes", json=NOTE).json()["note_id"] == "N-0002"  # ids are global
    assert api.get("/alerts/ALR-00850").json()["notes"][0]["alert_id"] == "ALR-00850"


def test_remove_hides_the_note_but_keeps_it_in_the_audit_trail(api):
    nid = api.post("/alerts/ALR-00405/notes", json=NOTE).json()["note_id"]
    r = api.delete(f"/alerts/ALR-00405/notes/{nid}", params={"investigator": "A. Lee"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["removed"] is True and d["removed_by"] == "A. Lee" and d["note_id"] == nid and d["recorded_at"]
    assert api.get("/alerts/ALR-00405").json()["notes"] == []
    assert api.delete(f"/alerts/ALR-00405/notes/{nid}", params={"investigator": "A. Lee"}).status_code == 404

    rows = [x for x in api.get("/audit").json()["decisions"] if x.get("note_id") == nid]
    assert [(x["decision"], x["investigator"]) for x in rows] == [("AI note removed", "A. Lee"),
                                                                 ("AI note pinned", "J. Doe")]  # newest first
    assert all(x["player_id"] == "P00405" and NOTE["question"] in x["note"] for x in rows)
    csv_rows = list(csv.DictReader(io.StringIO(api.get("/audit.csv").text)))
    assert {r["decision"] for r in csv_rows if r["alert_id"] == "ALR-00405"} >= {"AI note pinned", "AI note removed"}


def test_notes_survive_a_restart(api):
    from backend.app import main
    nid = api.post("/alerts/ALR-00405/notes", json=NOTE).json()["note_id"]
    assert api.notes_file.exists()
    main.store.notes = {}
    main.store.load()
    assert [n["note_id"] for n in main.store.active_notes("ALR-00405")] == [nid]


def test_report_lists_active_notes_escaped(api):
    hostile = {**NOTE, "answer": "<script>alert(1)</script> deposits rose"}
    keep = api.post("/alerts/ALR-00405/notes", json=hostile).json()["note_id"]
    gone = api.post("/alerts/ALR-00405/notes", json={**NOTE, "answer": "REMOVED NOTE TEXT"}).json()["note_id"]
    api.delete(f"/alerts/ALR-00405/notes/{gone}", params={"investigator": "A. Lee"})
    html = api.get("/alerts/ALR-00405/report").text
    assert "AI notes" in html and "AI-generated, reviewed by J. Doe" in html and keep
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert "REMOVED NOTE TEXT" not in html


def test_errors(api):
    assert api.post("/alerts/ALR-00405/notes", json={**NOTE, "investigator": "  "}).status_code == 422
    assert api.post("/alerts/ALR-00405/notes", json={**NOTE, "answer": ""}).status_code == 422
    assert api.post("/alerts/ALR-99999/notes", json=NOTE).status_code == 404
    nid = api.post("/alerts/ALR-00405/notes", json=NOTE).json()["note_id"]
    assert api.delete(f"/alerts/ALR-00405/notes/{nid}").status_code == 422  # no investigator
    assert api.delete(f"/alerts/ALR-00850/notes/{nid}", params={"investigator": "A"}).status_code == 404  # wrong alert
    assert api.delete("/alerts/ALR-00405/notes/N-9999", params={"investigator": "A"}).status_code == 404


def test_cors_allows_delete(api):
    r = api.options("/alerts/ALR-00405/notes/N-0001", headers={
        "Origin": "http://localhost:5500", "Access-Control-Request-Method": "DELETE"})
    assert r.status_code == 200 and "DELETE" in r.headers["access-control-allow-methods"]
