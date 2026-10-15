# Chat Contract: `/chat` and notes

> **Agreed between the frontend (branch `frontend-chat`) and the backend teammate.** Neither side changes these shapes without telling the other first.
>
> §1 is copied **verbatim** from section 11 of [CHAT_PANEL_PLAN.md](CHAT_PANEL_PLAN.md). §2 lists how the frontend fills and reads each field (no shape changes). §3 lists the points the backend must confirm. §4 gives example stub responses; the frontend's built-in stub (`?chat=stub`) returns exactly these shapes.

## 1. The contract (verbatim from the plan, §11)

```
New endpoint
  POST /chat
  Request:
    {
      "messages": [ {"role": "user" | "assistant" | "divider", "content": "..."} ],  // last ~12
      "context":  { "view": "queue" | "overview" | "alert", "alert_id": "ALR-00405" | null,
                    "filters": {...}, "sort": "-score", "visible_count": 156 },
      "question": "Summarise the top 5 structuring alerts"
    }
  Response:
    {
      "answer": "...",
      "provider": "groq", "model": "openai/gpt-oss-20b", "fallback_used": false,
      "verified": true, "unverified_numbers": [], "unknown_ids": [],
      "cases_used": ["ALR-00405", "ALR-00850", ...],
      "actions": [ {"type": "open_alert", "alert_id": "ALR-00405", "label": "Open ALR-00405"},
                   {"type": "apply_filter", "filters": {"type": "structuring"},
                    "label": "Show structuring alerts"} ],
      "assumption": "Taking 'recent' as the last 30 days." | null
    }

New endpoints for pinning
  POST   /alerts/{alert_id}/notes      { question, answer, provider, model, verified, investigator }
  DELETE /alerts/{alert_id}/notes/{note_id}?investigator=...
  Notes are stored next to decisions (data/decisions.json now; the database if the backend
  teammate moves to SQLite) and included in /alerts/{id}, /audit, /audit.csv and the case report.
```

## 2. How the frontend uses it

### Request (what the frontend sends)

```json
{
  "messages": [
    {"role": "user", "content": "Summarise the top 5 structuring alerts."},
    {"role": "assistant", "content": "1. ALR-00405 (P00405) ..."},
    {"role": "divider", "content": "Now viewing ALR-00405 (P00405)"}
  ],
  "context": {
    "view": "alert",
    "alert_id": "ALR-00405",
    "filters": {"band": null, "team": "AML", "type": "structuring", "status": null,
                "confidence": null, "min_score": null, "search": null, "include_watchlist": false},
    "sort": "-score",
    "visible_count": 29
  },
  "question": "Is this one worse than the ones you listed?"
}
```

- `messages`: at most the last 12 entries, oldest first, before the new question. Frontend-only notices (offline, errors) are never sent.
- `context.filters`: always all eight keys; `null` when unset. Values are the dashboard's own (`band` = `Critical|High|Medium|Low`, `team` = `AML|Fraud|Safer Gambling`, `type` = an anomaly-type key from `/meta`, `status` = a status from `/meta`, `confidence` = `High|Medium|Low`, `min_score` = integer, `search` = the ID search text).
- `context.sort`: `"-key"` = descending, `"key"` = ascending. Keys: `score`, `last_activity`, `ai`, `player_id`, `top_reason`, `team`, `status`.
- `context.visible_count`: rows the queue shows with the current filters.

### Response (what the frontend reads)

| Field | Frontend behaviour |
|---|---|
| `answer` | Plain text, rendered with text nodes only (never HTML). `\n\n` = new paragraph; lines starting `- `, `* ` or `1.` = list items. IDs matching `P\d{5}`, `ALR-\d{5}`, `WL-\d{5}` become links unless listed in `unknown_ids` or not found in the loaded queue. |
| `provider`, `model` | Footer, e.g. "Groq gpt-oss-20b", "Ollama llama3.2 · local" (`ollama` is shown as local). `null` = no AI answered (offline note). |
| `fallback_used` | Footer adds "· fallback". |
| `verified`, `unverified_numbers` | "Numbers checked", or the warning line "Not found in the evidence: …". |
| `unknown_ids` | Warning line "Unknown ID, not in the data: …"; those IDs are never clickable. |
| `cases_used` | "Cases used: …" under the answer (clickable when known); also offered by Pin to case in Mode 1. |
| `actions` | Rendered as buttons only if valid (below); nothing runs until clicked. Max 4. The button text is written by the frontend; `label` is accepted but not displayed. |
| `assumption` | One line above the answer: "Assumption: …". |

**Action whitelist** (anything else is dropped):

| `type` | Fields | Valid values |
|---|---|---|
| `open_alert` | `alert_id`, `label` | an existing `ALR-\d{5}` / `WL-\d{5}`, not in `unknown_ids` |
| `apply_filter` | `filters`, `label` | keys only `band`, `team`, `type`, `status`, `confidence`, `min_score`; values as in the request |
| `sort` | `sort`, `label` | one of the sort values above |
| `show_watchlist` | `label` | — |

There is **no** decision action. The frontend has no code path from the chat to `/alerts/{id}/decision`.

### Errors

- HTTP 404 / 405 (no `/chat` yet) → notice "AI is unavailable: this API does not have the /chat endpoint yet. The rest of the dashboard works as usual."
- Network failure → "AI is unavailable: the API could not be reached."
- Any other non-2xx → "AI is unavailable: <status or detail>".

## 3. For the backend to confirm

Everything in this section that the plan's §11 does not spell out is a frontend proposal. Until the backend teammate confirms it, each item is **PROPOSED, needs backend confirmation**.

| # | Item | Status |
|---|---|---|
| 1 | **Context sort format:** `"-key"` = descending, `"key"` = ascending, keys `score`, `last_activity`, `ai`, `player_id`, `top_reason`, `team`, `status`. **Filters shape:** always all eight keys (`band`, `team`, `type`, `status`, `confidence`, `min_score`, `search`, `include_watchlist`), `null` when unset (§2). | **Confirmed** (backend, `/chat` on branch `chat-backend`) |
| 2 | **Action type names:** `sort` (field `sort`) and `show_watchlist` (no fields) for the plan's "Sort by <key>" and "Show watchlist". The plan names only `open_alert` and `apply_filter`. | **Confirmed** (backend) |
| 3 | **Offline answer shape:** the normal response with `provider: null`, `model: null` and the offline note in `answer` (example 4.7). | **Confirmed** (backend): also used when every provider fails |
| 4 | **Notes response shapes:** POST returns the stored note; DELETE returns `{note_id, alert_id, removed, removed_by, recorded_at}`; `GET /alerts/{id}` returns `notes: [...]` with the same note objects (example 4.8). The plan defines only the requests. | PROPOSED; notes endpoints not built yet (next backend step) |

Required on the backend side (from the plan, not proposals):

- **CORS must allow `DELETE`** for removing a pinned note. The API currently allows only `GET` and `POST` (`allow_methods=["GET", "POST"]` in `backend/app/main.py`).
- **Notes must appear in `GET /audit`, `/audit.csv` and the case report** (`/alerts/{id}/report`, "AI notes (AI-generated, reviewed by <name>)"), as plan §10 says. Removals are recorded in the audit trail too.

## 4. Example stub responses

The built-in stub (`?chat=stub`) answers from the data already on the page (the visible queue rows and the open alert); it never invents players, amounts or alerts. Trigger words in the question select the example:

| Question contains | Example |
|---|---|
| (anything else) | 4.1 normal answer |
| `top`, `summarise`, `summarize` | 4.2 IDs and actions |
| `recent`, `big` | 4.3 assumption |
| `numbers`, `unverified` | 4.4 unverified numbers |
| `unknown` | 4.5 unknown IDs |
| `fallback` | 4.6 fallback used |
| `offline` | 4.7 offline |
| `error` | HTTP-style error (notice) |
| `xss` | 4.9 hostile text (must render as plain text) |

IDs, scores and counts below are illustrative; the stub fills them from the real rows on screen.

### 4.1 Normal answer

```json
{
  "answer": "The queue shows 156 alerts with the current filters. The highest score on screen is 97.",
  "provider": "stub", "model": "built-in", "fallback_used": false,
  "verified": true, "unverified_numbers": [], "unknown_ids": [],
  "cases_used": [],
  "actions": [],
  "assumption": null
}
```

### 4.2 Answer with clickable IDs and actions

```json
{
  "answer": "Top 3 alerts in the current view:\n1. ALR-00405 (P00405), score 97: Deposits kept just under $10,000\n2. ALR-01444 (P01444), score 97: Deposits far above declared income\n3. ALR-00850 (P00850), score 95: Cash in, cash out with little betting",
  "provider": "stub", "model": "built-in", "fallback_used": false,
  "verified": true, "unverified_numbers": [], "unknown_ids": [],
  "cases_used": ["ALR-00405", "ALR-01444", "ALR-00850"],
  "actions": [
    {"type": "open_alert", "alert_id": "ALR-00405", "label": "Open ALR-00405"},
    {"type": "apply_filter", "filters": {"band": "Critical"}, "label": "Show Critical alerts"},
    {"type": "sort", "sort": "-last_activity", "label": "Sort by most recent"},
    {"type": "show_watchlist", "label": "Show watchlist"}
  ],
  "assumption": null
}
```

### 4.3 Assumption line

```json
{
  "answer": "12 alerts in the current view had activity in the last 30 days of the data window.",
  "provider": "stub", "model": "built-in", "fallback_used": false,
  "verified": true, "unverified_numbers": [], "unknown_ids": [],
  "cases_used": [], "actions": [],
  "assumption": "Taking 'recent' as the last 30 days of the data window."
}
```

### 4.4 Unverified numbers

```json
{
  "answer": "ALR-00405 deposited about $48,000 over 6 weeks.",
  "provider": "stub", "model": "built-in", "fallback_used": false,
  "verified": false, "unverified_numbers": ["48,000", "6"], "unknown_ids": [],
  "cases_used": ["ALR-00405"], "actions": [], "assumption": null
}
```

### 4.5 Unknown IDs

```json
{
  "answer": "P99999 does not appear in the alert data. ALR-00405 does.",
  "provider": "stub", "model": "built-in", "fallback_used": false,
  "verified": true, "unverified_numbers": [], "unknown_ids": ["P99999"],
  "cases_used": ["ALR-00405"],
  "actions": [{"type": "open_alert", "alert_id": "P99999", "label": "Open P99999"}],
  "assumption": null
}
```

The `open_alert` action above is invalid (wrong pattern, and unknown) and must not render.

### 4.6 Fallback used

```json
{
  "answer": "The queue shows 156 alerts with the current filters.",
  "provider": "ollama", "model": "llama3.2", "fallback_used": true,
  "verified": true, "unverified_numbers": [], "unknown_ids": [],
  "cases_used": [], "actions": [], "assumption": null
}
```

Footer: "Ollama llama3.2 · local · fallback · Numbers checked".

### 4.7 Offline

```json
{
  "answer": "The AI assistant is offline: neither Groq nor Ollama answered. The rest of the dashboard works as usual.",
  "provider": null, "model": null, "fallback_used": true,
  "verified": true, "unverified_numbers": [], "unknown_ids": [],
  "cases_used": [], "actions": [], "assumption": null
}
```

An HTTP error (or no `/chat` at all) is shown by the frontend as a notice instead (§2 Errors).

### 4.8 Notes

`POST /alerts/ALR-00405/notes`

```json
{"question": "Why is this player High confidence?", "answer": "...", "provider": "groq",
 "model": "openai/gpt-oss-20b", "verified": true, "investigator": "J. Doe"}
```

Response `201` (proposed):

```json
{
  "note_id": "N-0001", "alert_id": "ALR-00405",
  "question": "Why is this player High confidence?", "answer": "...",
  "provider": "groq", "model": "openai/gpt-oss-20b", "verified": true,
  "investigator": "J. Doe", "recorded_at": "2026-10-15 14:02:11 UTC"
}
```

Errors: `422` when `investigator` is empty; `404` for an unknown alert.

`DELETE /alerts/ALR-00405/notes/N-0001?investigator=J.%20Doe` → `200` (proposed):

```json
{"note_id": "N-0001", "alert_id": "ALR-00405", "removed": true,
 "removed_by": "J. Doe", "recorded_at": "2026-10-15 14:05:40 UTC"}
```

`GET /alerts/ALR-00405` gains (proposed): `"notes": [ <note objects as above, not removed> ]`.

### 4.9 Hostile text (stub test only)

```json
{
  "answer": "<img src=x onerror=alert(1)> <script>alert(2)</script> ALR-00405",
  "provider": "stub", "model": "built-in", "fallback_used": false,
  "verified": true, "unverified_numbers": [], "unknown_ids": [],
  "cases_used": [], "actions": [], "assumption": "<b>not bold</b>"
}
```

Must render as literal text; only `ALR-00405` becomes a link.

## 5. Backend implementation notes (`/chat`, branch `chat-backend`)

No shapes changed. How the backend fills the contract:

- **Actions are built by the backend from its retrieval, never by the model:** `apply_filter` when the question names filters that differ from the queue's, `sort` for ranking words ("most recent"), `show_watchlist` when the question mentions the watchlist, then `open_alert` for cases named in the answer (not the open alert). At most 4. `label` is always sent.
- **`cases_used`** = alerts named in the answer, in order (player IDs resolved to their alert); in the alert view with no ID named, the open alert.
- **`unknown_ids`** = IDs in the answer that resolve to no alert or watchlist entry.
- **`assumption`** = the model's first line when it starts with "Assumption:"; removed from `answer`.
- **Never ask back:** trailing questions and offers are stripped; a question inside the answer triggers one regeneration, then the offending sentences are stripped.
- **Provider:** Groq first; a short Groq rate limit (up to 10 s) is waited out once, otherwise the same request goes to local Ollama (`fallback_used: true`). If none answers, the offline shape (example 4.7) is returned with HTTP 200.
- **Evidence size:** capped at about 4,000 tokens, below the plan's 6,000 words, because Groq's free tier allows 8,000 tokens per minute for the whole request. Queue rows are trimmed first; `left_out` tells the model how many were cut.
- **Not built:** plan section 7 layer 2 (model-driven lookup tools). Layer 1 retrieval answers the plan's test questions.
- **Known limit of the number check:** it confirms every number appears somewhere in the evidence, not that it is attached to the right fact.

