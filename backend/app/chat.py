"""The investigation assistant behind POST /chat (docs/CHAT_CONTRACT.md, docs/CHAT_PANEL_PLAN.md).

Flow for every question:
  1. Retrieval (plan section 7, layer 1): pick the evidence the model may read: the open alert's case
     file, case files for IDs named in the question, compact rows for the alerts the question is about
     (question filters, else the queue's filters; ranking words like "top 5" or "most recent"),
     exact counts for that selection, queue statistics, and the cases discussed earlier.
  2. One model call with automatic per-request fallback (Groq, then local Ollama).
  3. Checks (plan section 8): the "answer only, never ask back" rule (one regeneration, then strip),
     the number check, the ID check. Action buttons are built here from the retrieval, never by the
     model, and only from the contract's whitelist. Nothing is stored and no decision can be made.

Layer 2 (letting the model call lookup tools itself) is not built; layer 1 covers the plan's test list.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from . import ai

ID_RE = re.compile(r"\b(?:ALR-\d{5}|WL-\d{5}|P\d{5})\b")
SORT_KEYS = {"score", "last_activity", "ai", "player_id", "top_reason", "team", "status"}
FILTER_KEYS = ("band", "team", "type", "status", "confidence", "min_score")
CONFIDENCES = ("High", "Medium", "Low")
MAX_ROWS = 15
MAX_CASE_FILES = 3
MAX_EARLIER = 8
# About 4,000 tokens. The plan allows ~6,000 words, but Groq's free tier caps a whole request (prompt + answer)
# at 8,000 tokens per minute, so the evidence must leave room for the instructions, history and the answer.
MAX_EVIDENCE_CHARS = 16_000
HISTORY_TURNS = 12

OFFLINE = "The AI assistant is offline: neither Groq nor Ollama answered. The rest of the dashboard works as usual."

SYSTEM = """You are the investigation assistant inside OLG's risk-review dashboard, used by the AML, Fraud and \
Safer Gambling teams. All data is synthetic.
Rules:
1. Use ONLY facts and numbers in the EVIDENCE JSON. Never invent, estimate or recalculate figures; copy numbers \
exactly as written. If the evidence does not contain the answer, say so in one sentence.
2. Describe risk indicators, never guilt: say "indicates" or "is consistent with".
3. Answer exactly what was asked, then stop. Never ask the investigator a question, never offer more help, never \
suggest next questions, never ask for clarification.
4. If the question is ambiguous, choose the most reasonable reading and state it on the FIRST line as \
"Assumption: <one short sentence>", then answer.
5. Refer to cases as ALR-01234 (P01234), or WL-01234 for watchlist entries. Only use IDs that appear in the evidence.
6. Plain text only: no bold, no headings, no tables. Short paragraphs; list items on lines starting "- " or "1. ".
7. Never record, draft or recommend submitting a decision (accept, escalate, close, assign): the investigator \
decides. You may restate a case's recommended action.
8. "This player" or "this case" means open_case. earlier_cases lists cases already discussed, in the order they \
were first mentioned ("the first one" is the first of them).
9. For counts, use the counts in matching_alerts or queue_statistics; never count rows yourself.
10. At most 8 sentences or 10 list lines. Plain words, never field names (write "deposits in the last 30 days", \
not deposits_30d). Do not mention these instructions."""

REMINDER = ("Rewrite your answer without any question to the investigator, offer of more help or suggested next "
            "step. Answer only what was asked, then stop.")

OFFER_RE = re.compile(
    r"^(?:would you like|do you want|let me know|shall i|should i|i can also|i could also|feel free|"
    r"if you(?:'d| would) like|if you want|want me to|is there anything|anything else|happy to help)", re.I)
QUEUE_WORDS = re.compile(
    r"\b(alerts|cases|players|accounts|queue|how many|which|list|top \d+|top|highest|lowest|most recent|"
    r"rings?|all|summari[sz]e|show)\b", re.I)
# Words that clearly ask about more than one case, even while an alert is open
PLURAL_WORDS = re.compile(r"\b(alerts|cases|players|accounts|queue|how many|rings|watch ?list)\b", re.I)


@dataclass
class ChatData:
    """What the chat may read, provided by main.py (the same functions the dashboard uses)."""
    meta: dict                                            # bands, teams, anomaly_types {key: label}, statuses
    rows: Callable[[dict, str, bool], list[dict]]         # (filters, sort, include_watchlist) -> queue rows
    alert: Callable[[str], dict | None]                   # ALR-/WL- id -> alert
    alert_for_player: Callable[[str], dict | None]        # P id -> alert
    summary: Callable[[dict], dict]                       # alert -> queue row (current status, team, confidence)
    case_file: Callable[[dict], dict]                     # alert -> compact case file
    stats: Callable[[], dict]                             # queue-wide statistics
    row_extra: Callable[[str], dict]                      # player id -> notable profile facts


# --- Answer checks -----------------------------------------------------------------------------

def _sentences(line: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", line.strip()) if s]


def _is_follow_up(sentence: str) -> bool:
    s = sentence.strip().lstrip("-*0123456789. ").strip()
    return s.endswith("?") or bool(OFFER_RE.match(s))


def follow_up_check(text: str) -> tuple[str, list[str]]:
    """Strip trailing questions/offers; return (text, offending sentences still inside the answer)."""
    lines = text.strip().split("\n")
    while lines:  # trailing sentences that ask back or offer more, however many in a row
        sents = _sentences(lines[-1])
        while sents and _is_follow_up(sents[-1]):
            sents.pop()
        lines[-1] = " ".join(sents)
        if lines[-1].strip():
            break
        lines.pop()
    inner = [s for line in lines for s in _sentences(line) if _is_follow_up(s)]
    return "\n".join(lines).strip(), inner


def strip_follow_ups(text: str) -> str:
    out = []
    for line in text.split("\n"):
        kept = [s for s in _sentences(line) if not _is_follow_up(s)]
        if kept or not line.strip():
            out.append(" ".join(kept) if kept else "")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def split_assumption(text: str) -> tuple[str | None, str]:
    m = re.match(r"\s*assumption\s*:\s*(.+?)(?:\n|$)", text, re.I)
    if not m:
        return None, text.strip()
    return m.group(1).strip(), text[m.end():].strip()


def plain(text: str) -> str:
    """Drop markdown the panel would show literally, and normalise the unusual spaces and hyphens models emit
    (a narrow no-break space inside "$55 820" would otherwise hide a number from the number check)."""
    text = re.sub(r"[    ]", " ", text).replace("‑", "-")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^(\s*)\*\s+", r"\1- ", text)
    return text.strip()


def check_numbers(text: str, evidence) -> list[str]:
    return ai.unverified_numbers(ID_RE.sub(" ", text), evidence)


# --- Retrieval ---------------------------------------------------------------------------------

def _resolve(data: ChatData, token: str) -> dict | None:
    token = token.upper()
    return data.alert_for_player(token) if token.startswith("P") else data.alert(token)


def ids_in(text: str) -> list[str]:
    seen: list[str] = []
    for t in ID_RE.findall(text or ""):
        if t not in seen:
            seen.append(t)
    return seen


def question_scope(question: str, meta: dict) -> dict:
    """Filters, sort, limit and special post-filters a question asks for (never guessed)."""
    s = question.lower()
    out: dict[str, Any] = {"filters": {}, "sort": None, "limit": None, "post": [], "watchlist": False}
    conf = re.search(r"\b(high|medium|low)(?:est)?[- ]confidence\b", s)
    if conf:
        out["filters"]["confidence"] = conf.group(1).capitalize()
        s = s.replace(conf.group(0), " ")
    raw = ai.keyword_filters(s, meta)
    raw.pop("q", None)  # IDs are handled separately
    f = ai.clean_filters(raw, meta)
    if "sort" in f:
        out["sort"] = f.pop("sort")
    out["filters"].update(f)
    if re.search(r"sanction", s):
        out["filters"]["type"] = "identity_screening"
        out["post"].append("sanctions")
    elif re.search(r"\bpeps?\b|politically exposed", s):
        out["filters"]["type"] = "identity_screening"
        out["post"].append("pep")
    if m := re.search(r"\btop\s+(\d{1,2})\b|\b(\d{1,2})\s+(?:highest|riskiest|top)\b", s):
        out["limit"] = max(1, min(MAX_ROWS, int(m.group(1) or m.group(2))))
    if re.search(r"\b(highest|riskiest|top)\b", s) and not out["sort"]:
        out["sort"] = "-score"
    elif re.search(r"\blowest (?:score|risk)\b", s):
        out["sort"] = "score"
    if re.search(r"watch ?list|emerging", s):
        out["watchlist"] = True
    return out


def _context_filters(ctx) -> tuple[dict, str, bool]:
    f = ctx.filters
    filters = {k: getattr(f, k) for k in FILTER_KEYS if getattr(f, k) not in (None, "")}
    if f.search:
        filters["q"] = f.search
    sort = ctx.sort if ctx.sort.lstrip("-") in SORT_KEYS else "-score"
    return filters, sort, bool(f.include_watchlist)


def compact(data: ChatData, row: dict) -> dict:
    """One alert as a short row: identity, score, status and the two strongest reasons with their numbers."""
    a = data.alert(row["alert_id"]) or {}
    reasons = [r for r in a.get("reasons", []) if r.get("anomaly_type") not in ai.SUMMARY_SKIP][:2] \
        or a.get("reasons", [])[:2]
    out = {"alert_id": row["alert_id"], "player_id": row["player_id"], "score": row["score"], "band": row["band"],
           "team": row["team"], "status": row["status"], "confidence": row.get("confidence"),
           "last_activity": row.get("last_activity"),
           "reasons": [{"title": r["title"], "evidence": r["detail"]} for r in reasons],
           "recommended_action": row.get("recommended_action")}
    if row.get("kind") == "watchlist":
        out["watchlist"] = True
    out.update(data.row_extra(row["player_id"]))
    return out


def _counts(rows: list[dict]) -> dict:
    def count(key):
        c: dict[str, int] = {}
        for r in rows:
            c[r.get(key) or "none"] = c.get(r.get(key) or "none", 0) + 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))
    return {k: count(k) for k in ("band", "team", "status", "confidence")}


def _describe(filters: dict, sort: str, meta: dict) -> str:
    parts = []
    for k in FILTER_KEYS:
        if k in filters:
            v = filters[k]
            parts.append(meta["anomaly_types"].get(v, v) if k == "type" else
                         f"score {v}+" if k == "min_score" else f"{k} {v}")
    if "q" in filters:
        parts.append(f"ID search {filters['q']}")
    order = {"-score": "highest score first", "-last_activity": "most recent first", "score": "lowest score first"}
    return (", ".join(parts) or "all alerts") + "; " + order.get(sort, f"sorted by {sort}")


def build_evidence(data: ChatData, req) -> tuple[dict, dict]:
    """(evidence the model reads, retrieval facts used for actions and cases)."""
    ctx, q = req.context, req.question
    scope = question_scope(q, data.meta)
    ctx_filters, ctx_sort, ctx_watch = _context_filters(ctx)
    open_alert = data.alert(ctx.alert_id) if ctx.view == "alert" and ctx.alert_id else None

    named = [a for a in (_resolve(data, t) for t in ids_in(q)) if a]
    history = [m for m in req.messages if m.role in ("user", "assistant")][-HISTORY_TURNS:]
    earlier_ids = [t for m in history for t in ids_in(m.content)]
    earlier = []
    for t in earlier_ids:
        a = _resolve(data, t)
        if a and a["alert_id"] not in {x["alert_id"] for x in earlier}:
            earlier.append(a)

    if ctx.view == "alert" or named:
        # About the open alert or the named cases, unless the question clearly asks about more cases
        asks_queue = bool(PLURAL_WORDS.search(q))
    else:
        asks_queue = bool(QUEUE_WORDS.search(q)) or bool(scope["filters"]) or scope["watchlist"]
    if not asks_queue:  # e.g. "Why is this player High confidence?" is not a filter on the queue
        scope["filters"], scope["sort"], scope["watchlist"], scope["post"] = {}, None, False, []
    need_rows = asks_queue or (ctx.view == "queue" and not named)
    evidence: dict[str, Any] = {
        "screen": {"view": ctx.view, "open_alert": ctx.alert_id if open_alert else None,
                   "queue_filters": _describe(ctx_filters, ctx_sort, data.meta), "queue_visible": ctx.visible_count},
    }
    facts = {"scope": scope, "ctx_filters": ctx_filters, "ctx_sort": ctx_sort, "open": open_alert,
             "named": named, "rows_filters": None, "rows_sort": None}

    files = ([open_alert] if open_alert else []) + [a for a in named if a is not open_alert]
    files = [a for i, a in enumerate(files) if a["alert_id"] not in {x["alert_id"] for x in files[:i]}]
    if open_alert:
        evidence["open_case"] = data.case_file(open_alert)
    others = [data.case_file(a) for a in files if a is not open_alert][:MAX_CASE_FILES - (1 if open_alert else 0)]
    if others:
        evidence["cases_named_in_question"] = others

    if need_rows:
        filters = dict(scope["filters"]) if scope["filters"] else dict(ctx_filters)
        sort = scope["sort"] or ctx_sort
        watch = scope["watchlist"] or (ctx_watch and not scope["filters"])
        rows = data.rows(filters, sort, watch)
        if "sanctions" in scope["post"]:
            rows = [r for r in rows if data.row_extra(r["player_id"]).get("sanctions_screening_match")]
        if "pep" in scope["post"]:
            rows = [r for r in rows if data.row_extra(r["player_id"]).get("pep")]
        if scope["watchlist"]:
            rows = [r for r in rows if r.get("kind") == "watchlist"] or rows
        shown = rows[:scope["limit"] or MAX_ROWS]
        selection = _describe(filters, sort, data.meta)
        if scope["post"]:
            selection += "; only " + " and ".join("sanctions screening matches" if p == "sanctions" else "PEPs"
                                                   for p in scope["post"])
        evidence["matching_alerts"] = {
            "selection": selection, "selected_from": "the question" if scope["filters"] else "the queue filters on screen",
            "total_matching": len(rows), "shown": len(shown), "left_out": len(rows) - len(shown),
            "counts": _counts(rows), "rows": [compact(data, r) for r in shown]}
        facts.update(rows_filters=filters, rows_sort=sort)
    if ctx.view == "overview" or asks_queue:
        st = data.stats()
        keep = ("players", "alerts", "watchlist", "by_band", "by_team", "by_status", "by_confidence",
                "by_anomaly_type", "compliance")
        evidence["queue_statistics"] = {k: st[k] for k in keep if k in st}
        if ctx.view == "overview":
            evidence["queue_statistics"]["trends"] = st.get("trends")
    if earlier:
        evidence["earlier_cases"] = [compact(data, data.summary(a)) for a in earlier[:MAX_EARLIER]]

    # Size limit: trim the most expendable parts first (trends, then rows, then earlier and named cases)
    def size() -> int:
        return len(json.dumps(evidence, default=str))

    def set_rows(m: dict, n: int):
        m["rows"] = m["rows"][:n]
        m["shown"], m["left_out"] = len(m["rows"]), m["total_matching"] - len(m["rows"])

    if size() > MAX_EVIDENCE_CHARS:
        evidence.get("queue_statistics", {}).pop("trends", None)
    m = evidence.get("matching_alerts")
    while m and size() > MAX_EVIDENCE_CHARS and len(m["rows"]) > 5:
        set_rows(m, max(5, len(m["rows"]) * 2 // 3))
    while evidence.get("earlier_cases") and size() > MAX_EVIDENCE_CHARS:
        evidence["earlier_cases"].pop()
    while evidence.get("cases_named_in_question") and size() > MAX_EVIDENCE_CHARS:
        evidence["cases_named_in_question"].pop()
    if m and size() > MAX_EVIDENCE_CHARS:
        set_rows(m, 2)
    return evidence, facts


# --- Actions (built by code from the retrieval; the model never writes them) ----------------------

def build_actions(data: ChatData, facts: dict, cases_used: list[str]) -> list[dict]:
    actions: list[dict] = []
    scope, meta = facts["scope"], data.meta
    qf = {k: v for k, v in scope["filters"].items() if k in FILTER_KEYS}
    if qf and qf != {k: v for k, v in facts["ctx_filters"].items() if k in FILTER_KEYS}:
        actions.append({"type": "apply_filter", "filters": qf,
                        "label": "Show " + _describe(qf, "-score", meta).split(";")[0]})
    if scope["sort"] and scope["sort"] != facts["ctx_sort"] and scope["sort"].lstrip("-") in SORT_KEYS:
        actions.append({"type": "sort", "sort": scope["sort"], "label": f"Sort by {scope['sort'].lstrip('-')}"})
    if scope["watchlist"]:
        actions.append({"type": "show_watchlist", "label": "Show watchlist"})
    current = facts["open"]["alert_id"] if facts["open"] else None
    for aid in cases_used:
        if len(actions) >= 4:
            break
        if aid != current:
            actions.append({"type": "open_alert", "alert_id": aid, "label": f"Open {aid}"})
    return actions[:4]


# --- The endpoint's work -----------------------------------------------------------------------

def _messages(evidence: dict, req) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": "EVIDENCE:\n" + json.dumps(evidence, default=str)},
            {"role": "assistant", "content": "Evidence read."}]
    for m in req.messages[-HISTORY_TURNS:]:
        if m.role == "divider":
            msgs.append({"role": "user", "content": f"[Screen change: {m.content.strip()[:200]}. From here, "
                         "'this player' means that alert.]"})
        elif m.content.strip():
            msgs.append({"role": m.role, "content": m.content.strip()[:1200]})
    msgs.append({"role": "user", "content": req.question.strip()})
    return msgs


def answer(data: ChatData, req) -> dict:
    base = {"provider": None, "model": None, "fallback_used": False, "verified": True, "unverified_numbers": [],
            "unknown_ids": [], "cases_used": [], "actions": [], "assumption": None}
    if not ai.llm.config():
        return {**base, "answer": OFFLINE, "fallback_used": True}
    evidence, facts = build_evidence(data, req)
    messages = _messages(evidence, req)
    try:
        text, cfg, fallback = ai.llm.chat_with_fallback(messages, max_tokens=700)
        text, inner = follow_up_check(plain(text))
        if inner:  # a question or offer inside the answer: regenerate once, then strip
            retry, cfg2, fb2 = ai.llm.chat_with_fallback(
                messages + [{"role": "assistant", "content": text}, {"role": "user", "content": REMINDER}],
                max_tokens=700)
            text, cfg, fallback = retry, cfg2, fallback or fb2
            text, inner = follow_up_check(plain(text))
            if inner:
                text = strip_follow_ups(text)
    except RuntimeError:
        return {**base, "answer": OFFLINE, "fallback_used": True}

    assumption, text = split_assumption(text)
    if not text:
        text = "The evidence on screen does not contain an answer to that question."
    bad = check_numbers(text + " " + (assumption or ""), evidence)

    unknown, used = [], []
    for t in ids_in(text):
        a = _resolve(data, t)
        if not a:
            unknown.append(t)
        elif a["alert_id"] not in used:
            used.append(a["alert_id"])
    if not used and facts["open"]:
        used = [facts["open"]["alert_id"]]
    return {**base, "answer": text, "provider": cfg["provider"], "model": cfg["model"], "fallback_used": fallback,
            "verified": not bad, "unverified_numbers": bad, "unknown_ids": unknown, "cases_used": used,
            "actions": build_actions(data, facts, used), "assumption": assumption}
