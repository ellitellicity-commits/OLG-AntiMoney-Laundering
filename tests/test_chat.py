"""POST /chat (docs/CHAT_CONTRACT.md): answer checks, retrieval scoping, actions and response shapes.

The model is replaced by a fake, so these tests are deterministic and never call Groq or Ollama.
Needs pipeline outputs in data/ (run .\\run_demo.ps1 or the pipeline scripts first); skipped otherwise.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.app import ai, chat

ROOT = Path(__file__).resolve().parents[1]
needs_data = pytest.mark.skipif(not (ROOT / "data" / "scores" / "alerts.json").exists(),
                                reason="run the pipeline first (data/scores/alerts.json missing)")
NO_FILTERS = {"band": None, "team": None, "type": None, "status": None, "confidence": None, "min_score": None,
              "search": None, "include_watchlist": False}
CONTRACT_KEYS = {"answer", "provider", "model", "fallback_used", "verified", "unverified_numbers", "unknown_ids",
                 "cases_used", "actions", "assumption"}
FAKE_CFG = {"provider": "groq", "model": "openai/gpt-oss-20b"}


# --- The "answer only, never ask back" check (plan section 5: unit-tested with example answers) -----

@pytest.mark.parametrize("text,expected", [
    ("ALR-00405 scores 97.", "ALR-00405 scores 97."),
    ("ALR-00405 scores 97. Would you like me to compare it with others?", "ALR-00405 scores 97."),
    ("ALR-00405 scores 97.\n\nLet me know if you need anything else.", "ALR-00405 scores 97."),
    ("Three alerts match. Do you want the list?", "Three alerts match."),
    ("- ALR-00405\n- ALR-00850\nShall I open the first one?", "- ALR-00405\n- ALR-00850"),
    ("Deposits rose 6x. I can also check the linked accounts. Feel free to ask.", "Deposits rose 6x."),
])
def test_trailing_follow_ups_are_stripped(text, expected):
    cleaned, inner = chat.follow_up_check(text)
    assert cleaned == expected and inner == []


def test_question_inside_the_answer_is_reported_then_strippable():
    text = "Is this structuring? The deposits are just under $10,000. The score is 97."
    cleaned, inner = chat.follow_up_check(text)
    assert inner == ["Is this structuring?"]
    assert chat.strip_follow_ups(cleaned) == "The deposits are just under $10,000. The score is 97."


def test_assumption_line_and_markdown():
    a, rest = chat.split_assumption("Assumption: taking 'recent' as the last 30 days.\nFive alerts match.")
    assert a == "taking 'recent' as the last 30 days." and rest == "Five alerts match."
    assert chat.split_assumption("No assumption here.") == (None, "No assumption here.")
    assert chat.plain("## Top\n**ALR-00405** scores 97\n* item") == "Top\nALR-00405 scores 97\n- item"
    assert chat.plain("$55 820 and split‑deposit") == "$55 820 and split-deposit"


def test_number_check_ignores_ids():
    assert chat.check_numbers("WL-02014 and ALR-00405 (P00405) scored 97.", {"score": 97}) == []
    assert chat.check_numbers("It deposited $48,000.", {"deposits": 55820}) == ["$48,000"]


# --- Endpoint, with a fake model ------------------------------------------------------------------

@pytest.fixture
def api(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from backend.app import main

    calls = []

    def fake(messages, max_tokens=700, temperature=0.2):
        calls.append(messages)
        return fake.reply(messages), FAKE_CFG, False
    fake.reply = lambda messages: "No answer."
    monkeypatch.setattr(ai.llm, "config", lambda: FAKE_CFG)
    monkeypatch.setattr(ai.llm, "chat_with_fallback", fake)
    monkeypatch.setattr(main, "DECISIONS_FILE", tmp_path / "decisions.json")
    with TestClient(main.app) as c:
        c.fake, c.calls = fake, calls
        yield c


def post(c, question, view="queue", alert_id=None, filters=None, messages=None, sort="-score"):
    r = c.post("/chat", json={"messages": messages or [], "question": question,
                              "context": {"view": view, "alert_id": alert_id, "filters": filters or NO_FILTERS,
                                          "sort": sort, "visible_count": 296}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == CONTRACT_KEYS
    return body


def evidence_of(c) -> str:
    return c.calls[-1][1]["content"]


@needs_data
def test_queue_question_shape_actions_and_ids(api):
    api.fake.reply = lambda m: ("Assumption: taking the top 5 by score.\nTop structuring alerts:\n"
                                "1. ALR-00405 (P00405), score 97\n2. P99999 is listed too\nWould you like more?")
    d = post(api, "Summarise the top 5 structuring alerts.")
    assert d["assumption"] == "taking the top 5 by score."
    assert "Would you like" not in d["answer"]
    assert d["unknown_ids"] == ["P99999"] and d["cases_used"] == ["ALR-00405"]
    assert d["provider"] == "groq" and d["fallback_used"] is False
    types = [a["type"] for a in d["actions"]]
    assert types[0] == "apply_filter" and d["actions"][0]["filters"] == {"type": "structuring"}
    assert {"type": "open_alert", "alert_id": "ALR-00405", "label": "Open ALR-00405"} in d["actions"]
    assert len(d["actions"]) <= 4
    for a in d["actions"]:  # contract whitelist: exact keys per type
        allowed = {"open_alert": {"type", "alert_id", "label"}, "apply_filter": {"type", "filters", "label"},
                   "sort": {"type", "sort", "label"}, "show_watchlist": {"type", "label"}}[a["type"]]
        assert set(a) == allowed
    ev = evidence_of(api)
    assert '"total_matching"' in ev and '"left_out"' in ev
    rows = re.findall(r'"alert_id": "(ALR-\d{5})"', ev)
    assert 0 < len(rows) <= 5  # "top 5"


@needs_data
def test_open_alert_question_is_not_read_as_a_queue_filter(api):
    api.fake.reply = lambda m: "Six independent kinds of evidence agree."
    d = post(api, "Why is this player High confidence?", view="alert", alert_id="ALR-00405")
    assert d["cases_used"] == ["ALR-00405"] and d["actions"] == []
    ev = evidence_of(api)
    assert '"open_case"' in ev and '"matching_alerts"' not in ev


@needs_data
def test_named_ids_get_case_files_not_queue_rows(api):
    api.fake.reply = lambda m: "ALR-00405 (P00405) and ALR-02426 (P02426) both show money movement."
    d = post(api, "Compare P00405 and P02426.")
    assert d["cases_used"] == ["ALR-00405", "ALR-02426"]
    ev = evidence_of(api)
    assert '"cases_named_in_question"' in ev and '"matching_alerts"' not in ev
    assert len(ev) < chat.MAX_EVIDENCE_CHARS + 200


@needs_data
def test_counts_and_earlier_cases_and_divider(api):
    api.fake.reply = lambda m: "41 alerts match."
    post(api, "How many Safer Gambling alerts are still New?")
    assert '"Safer Gambling"' in evidence_of(api) and '"counts"' in evidence_of(api)
    history = [{"role": "user", "content": "Summarise the top 5 structuring alerts."},
               {"role": "assistant", "content": "1. ALR-00850 (P00850)\n2. ALR-00405 (P00405)"},
               {"role": "divider", "content": "Now viewing ALR-01444 (P01444)"}]
    post(api, "Is this one worse than the first one?", view="alert", alert_id="ALR-01444", messages=history)
    ev, sent = evidence_of(api), api.calls[-1]
    assert ev.index("ALR-00850") < ev.index("ALR-00405")  # earlier cases kept in first-mentioned order
    assert any("Screen change: Now viewing ALR-01444" in m["content"] for m in sent)


@needs_data
def test_sanctions_question_selects_only_matches(api):
    api.fake.reply = lambda m: "Listed."
    post(api, "Which alerts have a sanctions screening match?")
    ev = evidence_of(api)
    assert ev.count('"sanctions_screening_match": true') == len(re.findall(r'"score": \d+, "band"', ev)) > 0


@needs_data
def test_regenerates_once_when_the_answer_asks_back(api):
    replies = iter(["Is it structuring? Deposits stay under $10,000.", "Deposits stay under $10,000."])
    api.fake.reply = lambda m: next(replies)
    d = post(api, "Why was ALR-00405 flagged?")
    assert d["answer"] == "Deposits stay under $10,000." and len(api.calls) == 2
    assert "Rewrite your answer" in api.calls[-1][-1]["content"]


@needs_data
def test_offline_shape(api, monkeypatch):
    monkeypatch.setattr(ai.llm, "config", lambda: None)
    d = post(api, "Anything?")
    assert d["provider"] is None and d["model"] is None and d["fallback_used"] is True
    assert d["answer"] == chat.OFFLINE and d["actions"] == [] and d["cases_used"] == []


@needs_data
def test_provider_errors_become_the_offline_answer(api, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("groq returned HTTP 413; fallback: ollama request failed")
    monkeypatch.setattr(ai.llm, "chat_with_fallback", boom)
    d = post(api, "Summarise the top 5 structuring alerts.")
    assert d["answer"] == chat.OFFLINE and d["provider"] is None


def test_rejects_bad_requests():
    from fastapi.testclient import TestClient

    from backend.app import main
    c = TestClient(main.app)
    assert c.post("/chat", json={"question": ""}).status_code == 422
    assert c.post("/chat", json={"question": "x", "messages": [{"role": "system", "content": "x"}]}).status_code == 422
