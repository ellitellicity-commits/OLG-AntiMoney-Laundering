# API Match: frontend mock vs. real backend

**For:** whoever builds the live `frontend/index.html`, and the backend developer.
**Date:** 2026-10-15.
**Compares:** the fields shown in `frontend/mock_frontend.html` and promised in [API_CONTRACT.md](API_CONTRACT.md) against what the backend actually returns.

## Where the backend is, and how this was checked

- **No backend exists on `main` or `frontend-mock`.** The backend lives only on the remote branch **`origin/backend`** (commit `6cb45fe`, "Add run_demo.ps1 one-command start"). This document is based on that branch:
  - `backend/app/main.py`, `schemas.py`, `store.py` and `network.py`;
  - `backend/pipeline/common.py` and `detect.py`;
  - `backend/README.md` and `docs/API.md`.
- **A second, different backend** is on `origin/wireframe` (commit `8d685bd`), together with its own live `frontend/index.html`, `app.js` and `styles.css`. It does not match `origin/backend`:
  - it has different status values (`New / In review / Escalated / Closed`);
  - it adds an `assign` decision;
  - it adds AI, watchlist and audit endpoints.

  This document does **not** analyse it in detail. See question Q1.
- **Not verified live.** Nothing was running on port 8000. Python is not installed on this machine, so the API could not be started. Port 5000 answers, but that is an unrelated app ("RetainIQ backend"), not this project.
- **What was checked instead:** the backend branch commits a real pipeline output, `data/scores/alerts.json` (193 alerts). The sums, counts and orderings below come from that file, which is exactly what `GET /alerts/{id}` serves. It is a pipeline output, not a live HTTP response.
- **Every row in the tables below is "from source, not verified live".**

---

## Summary

The field table compares **29 fields the mock displays** with the backend:

| Status | Count | Meaning |
|---|---|---|
| **Matches** | 7 | Same name and place. **5 of the 7 still differ in values or format** (IDs, band names, anomaly type names, status values, band counts) |
| **Renamed** | 15 | The data exists under another name, in another place or in another shape |
| **Missing** | 7 | The backend has no such field: `initials`, `age`, `province`, `activity_30d`, `locations`, `as_of`, `monitoring` |
| **Extra** | 24 | The backend returns these, but the mock does not show them |

**Biggest structural difference.** The mock gets one flat player object from `GET /players/{id}`. The real backend spreads the dossier over **five calls**:
- `GET /alerts/{alert_id}`
- `GET /players/{id}/peers`
- `GET /players/{id}/network`
- `GET /players/{id}/transactions`
- `GET /players/{id}`

There is no `GET /summary`. The closest equivalent is `GET /stats`.

**Score check:** the reason points do **not** add up to the risk score for **121 of 193 alerts** (63%). Details are in [Enums and formats → Score arithmetic](#score-arithmetic).

---

## Field table

Column "Real backend" gives the endpoint and JSON path. Status values are **matches**, **renamed**, **missing** and **extra**. "Verified" is the same for every row: *from source, not verified live*.

### Queue rows and header (mock: `PLAYERS[]`, ribbon, masthead)

| # | Mock field | Mock type / example | Where on screen | Real backend | Real type / example | Status | Verified |
|---|---|---|---|---|---|---|---|
| 1 | `player_id` | string `"P-10482"` | Queue row, dossier title, case number, linked list | `player_id` (every endpoint) | string `"P03247"`, with no hyphen and 5 digits | **matches** (format differs) | from source, not verified live |
| 2 | `initials` | string `"MR"` | Avatar circle in queue and linked list | none (the backend has no names at all) | n/a | **missing** | from source, not verified live |
| 3 | `risk_score` | int `91` | Queue badge, score ring, sum line | `score` (`/alerts`, `/alerts/{id}`, `/players/{id}`) | int `100`. Range 0–100; alerts are only 40–100 | **renamed** | from source, not verified live |
| 4 | `band` | enum `"high"` | Badge label and colour, ring, ribbon | `band` | `"Critical"` / `"High"` / `"Medium"` / `"Low"` (Title case, 4 values) | **matches** (values differ) | from source, not verified live |
| 5 | `status` | display label `"In review"` (contract: enum `in_review`) | Queue row tag, dossier stamp | `status` | `"open"` / `"accepted"` / `"escalated"` / `"closed"` | **matches** (values differ) | from source, not verified live |
| 6 | `top_reason` (contract) / `reasons[0].headline` (mock) | string `"Deposits are 7× declared monthly income"` | Queue row one-liner | `/alerts` → `items[].top_reason_title` | string `"Transactions from distant places too close together"` | **renamed** | from source, not verified live |
| 7 | `alerts` (list wrapper) | `{as_of, alerts:[…]}` | Whole queue | `/alerts` → `{total, limit, offset, items:[…]}` | Paginated, default `limit` 50, max 1000 | **renamed** | from source, not verified live |
| 8 | `activity_30d` | 30 numbers (CAD wagered per day) | Queue heat strip; "30-day activity" chart | none. Nearest: `/players/{id}/timeline` (weekly, not daily) or raw bets from `/players/{id}/transactions?type=bet&since=…` | Weekly series / transaction rows | **missing** | from source, not verified live |
| 9 | `as_of` | ISO datetime `"2026-10-14T14:32:00-04:00"` | "last scan 2026-10-14 14:32" | none. Nearest: `/stats` → `reference_date` | date only `"2026-10-01"`. This is the data cut-off, not the scan time | **missing** | from source, not verified live |
| 10 | `monitoring` | enum `active` / `stale` / `offline` | Pulsing "Monitoring" indicator | none. Nearest: `GET /health` → `{"status":"ok"}` | n/a | **missing** | from source, not verified live |
| 11 | `open_alerts` | int `8` | "8 open alerts" in the ribbon | `/stats` → `by_status.open` (or `alerts` for all statuses) | int | **renamed** | from source, not verified live |
| 12 | `by_band` | `{high, medium, low}`, open alerts only | Ribbon counts and bar | `/stats` → `by_band` | `{"Critical":100,"High":32,"Medium":61,"Low":0}`. Counts **all** alerts, whatever their status | **matches** (keys and meaning differ) | from source, not verified live |

### Dossier header and verdict (mock: `renderDossier`)

| # | Mock field | Mock type / example | Where on screen | Real backend | Real type / example | Status | Verified |
|---|---|---|---|---|---|---|---|
| 13 | `age` | int `24` | Header meta "24 yrs" | none. `profile.age_band` instead | string `"18-24"` | **missing** | from source, not verified live |
| 14 | `occupation` | string `"Student, part-time retail"` | Header meta | `profile.occupation` | string `"Retail associate"` | **renamed** (nested) | from source, not verified live |
| 15 | `income_band` | string `"Under $25k"` | Header meta | `profile.income_band` | `"<20k"`, `"20-40k"`, `"40-60k"`, `"60-100k"`, `"100-150k"`, `"150k+"` | **renamed** (nested; values differ) | from source, not verified live |
| 16 | `province` | string `"ON"` | Header meta; in/out-of-province flag | none. Nearest: `profile.home_region` | `"Toronto/GTA"`, `"Eastern Ontario"`, `"Central Ontario"`, `"Southwestern Ontario"`, `"Northern Ontario"` (all Ontario) | **missing** | from source, not verified live |
| 17 | `anomaly_types` | array, e.g. `["income_mismatch","location"]` | Tags under the score ring | `anomaly_types` | array, e.g. `["location_anomaly","behaviour_change","peer_deviation","income_mismatch","multivariate_outlier"]`, ordered by points | **matches** (values differ) | from source, not verified live |
| 18 | `recommended_action.label` | string `"Request source of funds"` | Action heading, primary button | `/alerts/{id}` → `recommended_action.action` (on `/alerts` rows it is a plain string `recommended_action`) | string `"Verify account owner and hold withdrawals to new payment methods"` | **renamed** | from source, not verified live |
| 19 | `recommended_action.team` | enum `"AML"` | Under the action | `recommended_action.team` | `"AML"` / `"Fraud"` / `"Safer Gambling"` | **matches** | from source, not verified live |
| 20 | `recommended_action.rationale` | string | Under the action | `recommended_action.rationale` | string. It is fixed per anomaly type, **not** filled with this player's numbers | **matches** | from source, not verified live |

### Evidence thread (mock: `reasons[]`)

| # | Mock field | Mock type / example | Where on screen | Real backend | Real type / example | Status | Verified |
|---|---|---|---|---|---|---|---|
| 21 | `reasons[].type` | `income_mismatch` / `peer_deviation` / `location` / `behaviour_change` / `network` | Uppercase label on each card | `reasons[].anomaly_type` | adds `cash_cycling`, `multivariate_outlier`; uses `location_anomaly` and `linked_players` | **renamed** (values differ) | from source, not verified live |
| 22 | `reasons[].headline` | string ≤ 60 chars | Card title | `reasons[].title` | `"Withdrawals to a new payment method from a new device"` | **renamed** | from source, not verified live |
| 23 | `reasons[].evidence` | **sentence** with numbers | Card body | `reasons[].detail` | `"6 withdrawal(s) went to a payment method first seen this month, alongside 1 new device(s)."` Note: the backend's own `evidence` is an **object** of numbers, so the name clashes | **renamed** | from source, not verified live |
| 24 | `reasons[].weight` | int points | "+36 points", bar, sum line | `reasons[].points` | int. Points **before** the per-type cap, so they don't add up to the score | **renamed** (meaning differs) | from source, not verified live |

### Peer comparison, activity, locations, network

| # | Mock field | Mock type / example | Where on screen | Real backend | Real type / example | Status | Verified |
|---|---|---|---|---|---|---|---|
| 25 | `monthly_spend` | number CAD `14850` | Player diamond on strip plot; ratios | `/players/{id}/peers` → `features[feature="deposits_30d"].value`. Also `/alerts/{id}` → `key_metrics.deposits_30d` | number, e.g. `5370.0` | **renamed** | from source, not verified live |
| 26 | `peer_median` | number CAD `310` | Solid tick, legend, ratio | `/players/{id}/peers` → `features[deposits_30d].peer_median` | number or `null`, e.g. `20.0` | **renamed** | from source, not verified live |
| 27 | `peer_p90` | number CAD `1120` | Dashed tick, shaded range | `/players/{id}/peers` → `features[deposits_30d].peer_p90` | number or `null`, e.g. `90.0` | **renamed** | from source, not verified live |
| 28 | `locations[]` | `[{region:"Toronto, ON", count:171}]` | "Locations" list and province flag | none. Derivable from `ip_region` on `/players/{id}/transactions` | `ip_region` values: the 5 Ontario regions, `"Quebec"`, `"Manitoba"`, `"British Columbia"`, `"US - New York"`, `"US - Florida"`, `"US - Nevada"`, `"United Kingdom"`, `"Malta"`, `"Cyprus"`, `"Romania"` | **missing** | from source, not verified live |
| 29 | `linked_players[]` | `[{player_id, link:"Shared device D-7F31 · shared card ending 4417"}]` | "Linked players" list | `/players/{id}/network` → `nodes[]` (`id`, `score`, `band`, `alert_id`) + `edges[]` (`source`, `target`, `shared:[{type,value}]`, `opposite_bets`). Up to 2 hops by default | Graph, not a list | **renamed** (restructured) | from source, not verified live |

### Extra: returned by the backend, not shown in the mock

| # | Backend field | Where | Example | Status | Verified |
|---|---|---|---|---|---|
| E1 | `alert_id` | `/alerts`, `/alerts/{id}`, network nodes | `"A-P03247"`. **Every alert and decision endpoint is keyed by this, not by `player_id`** | **extra** | from source, not verified live |
| E2 | `rank` | `/alerts`, `/alerts/{id}` | `1` | **extra** | from source, not verified live |
| E3 | `team` (alert level) | `/alerts`, `/alerts/{id}`, `/players/{id}` | `"Fraud"` | **extra** | from source, not verified live |
| E4 | `reason_count` | `/alerts` | `7` | **extra** | from source, not verified live |
| E5 | `created_at` | `/alerts`, `/alerts/{id}` | `"2026-10-01"` (same for all 193) | **extra** | from source, not verified live |
| E6 | `profile.age_band` | `/alerts`, `/alerts/{id}`, `/players/{id}` | `"18-24"` | **extra** | from source, not verified live |
| E7 | `profile.home_region` | same | `"Toronto/GTA"` | **extra** | from source, not verified live |
| E8 | `profile.signup_date` | same | `"2025-09-06"` | **extra** | from source, not verified live |
| E9 | `peer_group`, `peer_group_size` | `/alerts/{id}`, `/players/{id}`, `/peers` | `"18-24 \| 20-40k \| Toronto/GTA"`, `59` | **extra** | from source, not verified live |
| E10 | `points_by_type` | `/alerts/{id}` | `{"location_anomaly":50,"behaviour_change":42,…}` (capped at 50 per type) | **extra** | from source, not verified live |
| E11 | `raw_points` | `/alerts/{id}` | `193` (sum before any cap) | **extra** | from source, not verified live |
| E12 | `iforest_percentile` | `/alerts/{id}` | `0.9976` | **extra** | from source, not verified live |
| E13 | `key_metrics` | `/alerts/{id}` | `deposits_30d`, `withdrawals_30d`, `turnover_30d`, `net_loss_30d` (can be negative), `bet_count_30d`, `avg_stake_30d`, `deposits_baseline_m`, `monthly_income_estimate` | **extra** | from source, not verified live |
| E14 | `summary` | `/alerts/{id}` | Template sentence built from evidence | **extra** | from source, not verified live |
| E15 | `latest_decision` | `/alerts/{id}` | `null` or `{decision, note, reason, investigator, created_at}` | **extra** | from source, not verified live |
| E16 | `reasons[].code` | `/alerts/{id}` | `"IMPOSSIBLE_TRAVEL"` | **extra** | from source, not verified live |
| E17 | `reasons[].evidence` (object) | `/alerts/{id}` | `{"impossible_travel_count_30d":3,"distinct_ip_regions_30d":3}` | **extra** | from source, not verified live |
| E18 | `reasons[].comparison` | `/alerts/{id}` | `{"peer_median":0,"own_baseline":null}` | **extra** | from source, not verified live |
| E19 | `recommended_action.secondary[]` | `/alerts/{id}` | `[{"team":"Safer Gambling","action":"…"}]` | **extra** | from source, not verified live |
| E20 | `recommended_action.primary_type` | `/alerts/{id}` (not declared in `schemas.py`, so `/docs` may not show it) | `"location_anomaly"` | **extra** | from source, not verified live |
| E21 | `total`, `limit`, `offset` | `/alerts`, `/players/{id}/transactions` | `193, 50, 0` | **extra** | from source, not verified live |
| E22 | Peer extras: `own_baseline`, `peer_q1`, `peer_q3`, `z_score`, `percentile`, `flagged`, plus 5 more features (`avg_stake_30d`, `bets_per_day_30d`, `net_loss_30d`, `turnover_30d`, `max_deposit_30d`) | `/players/{id}/peers` | `z_score: 8.43, flagged: true` | **extra** | from source, not verified live |
| E23 | Network extras: `cluster_size`, `cluster_avg_score`, `summary`, `opposite_bets` | `/players/{id}/network` | `5, 100.0, "Directly linked to 4 player(s)…"` | **extra** | from source, not verified live |
| E24 | Stats extras: `reference_date`, `players`, `by_team`, `by_type`, `by_status`, `score_histogram`, `synthetic` | `/stats` | `players: 5000` | **extra** | from source, not verified live |

The backend also has endpoints that the mock doesn't use: `/meta`, `/validation`, `/alerts/export.csv`, `/alerts/{id}/decisions`, `/alerts/{id}/report`, `/players/{id}/timeline` and `/network/clusters`.

---

## Enums and formats

All from source, not verified live.

### Risk bands

| | Mock / contract | Backend (`common.py` `BANDS`) |
|---|---|---|
| Values | `low`, `medium`, `high` (lowercase) | `Low`, `Medium`, `High`, `Critical` (Title case) |
| Cut-offs | Low 0–39, Medium 40–69, High 70–100 | Low 0–39, Medium 40–69, High 70–89, **Critical 90–100** |
| Count in queue (committed data) | n/a | Critical **100**, High 32, Medium 61, Low **0** |

- The backend still uses the earlier 4-band draft that the docs replaced with 3 bands.
- More than half of the queue (100 of 193) is Critical.
- The mock's meter already lights a 4th bar at 90+, so Critical can be shown as "High + 4th bar" without a new colour.

### Alerts only exist at score 40 or higher

`ALERT_MIN_SCORE = 40`, so **no Low alert ever reaches the queue**. The mock shows 2 Low alerts (P-71845 at 32, P-88120 at 18), a Low count in the ribbon and a Low filter. With real data, all of these are always empty or 0.

### Anomaly types

| Mock / contract | Backend `anomaly_type` | Notes |
|---|---|---|
| `income_mismatch` | `income_mismatch` | same |
| `peer_deviation` | `peer_deviation` | same |
| `location` | `location_anomaly` | renamed |
| `behaviour_change` | `behaviour_change` | same |
| `network` (reasons only) | `linked_players` | renamed. The mock's `TYPE_LABEL` already says "Linked players" |
| none | `cash_cycling` | **new** (AML: money in and out with little betting) |
| none | `multivariate_outlier` | **new** (Isolation Forest). Appears on 176 of 193 alerts |

- The contract says `anomaly_types` should exclude `network`. The backend includes `linked_players` and `multivariate_outlier` in `anomaly_types`.
- `/meta` and the `/alerts?type=` filter also list `linked_ring`, which is a data-generation scenario name and never appears on an alert.

### Status

| Mock label | Contract enum | Backend `status` | Backend decision that sets it |
|---|---|---|---|
| New | `new` | `open` | (default) |
| In review | `in_review` | none | none |
| Awaiting info | `awaiting_info` | none | none |
| Escalated | `escalated` | `escalated` | `escalate` |
| Dismissed | `dismissed` | `closed` | `close` (needs `reason` or `note`, else 422) |
| none | none | `accepted` | `accept` (follow the recommendation) |

All 193 committed alerts are `open`. Status only changes through `POST /alerts/{alert_id}/decision` and is kept in `data/decisions.db` (SQLite).

### IDs

| Item | Mock | Backend |
|---|---|---|
| Player | `P-10482` | `P00001`–`P05000` |
| Alert | none (the mock uses `player_id`) | `A-P03247` |
| Case number (frontend-built) | `"Case SNT-2026-" + player_id.slice(2)` → `SNT-2026-10482` | The same code on `P03247` gives `SNT-2026-3247`, which drops a digit. Use `player_id.slice(1)` |
| Linked player string | `Shared device D-7F31 · shared card ending 4417` | `shared: [{type:"device", value:"DEV-ULC2FSQH"}, {type:"payment_method", value:"PM-TJC0T1SK"}]`. Type values: `device`, `payment_method`, `address` |

### Numbers and money

- Money is a plain number in CAD in both, so this **matches**. The backend rounds to 2 decimals (`1803.69`), while the mock uses whole dollars. `cad()` in the mock uses `toLocaleString("en-CA")`, which will show the decimals.
- `net_loss_30d` can be **negative** (the player won money).
- `peer_median` and `peer_p90` can be **`null`** when a peer group has no stats, and can be very small (`20.0`). The mock's peer chart is a log scale clamped to $100–$30,000, so a $20 median is drawn at $100.
- Ratios are not sent. The frontend computes `value / peer_median`, which **divides by zero** when `peer_median` is 0 or `null`.

### Dates and times

| Field | Contract | Backend |
|---|---|---|
| Scan time / `as_of` | ISO 8601 with Toronto offset, `2026-10-14T14:32:00-04:00` | none. `reference_date` is a date only, `"2026-10-01"` |
| Alert `created_at` | n/a | date only, `"2026-10-01"` |
| Decision `created_at` | n/a | UTC with offset, `"2026-10-15T13:42:10+00:00"` |
| Transaction `timestamp` | n/a | **no timezone**, `"2026-09-28 21:12:00"` (space, not `T`) |

- The mock's activity chart hardcodes the axis labels "Sep 15 / Sep 30 / Oct 14".
- The real 30-day window is **2026-09-01 to 2026-09-30** (`reference_date` 2026-10-01 minus 30 days).

### Score range

- Both use an integer 0–100.
- In the committed data, scores run from 40 to 100, and **79 alerts are exactly 100**.
- Ties are broken by `raw_points`, then `iforest_percentile`, then `player_id`, and the result is stored as `rank`.

### Score arithmetic

The mock prints "points total X = risk score X" under "Why flagged". The contract requires the reason weights to add up to the score.

**The mock's own data passes this check.** All 8 players add up (91, 84, 76, 63, 55, 47, 32, 18).

**The backend's data does not.** In `detect.py` `combine()`:
- reasons are summed **per anomaly type**;
- each type is **capped at 50**;
- the total is **capped at 100**.

Checked against the 193 committed alerts:

| Check | Alerts that pass | Alerts that fail |
|---|---|---|
| Sum of `reasons[].points` = `score` | 72 | **121** (the sum is always higher) |
| Sum of `points_by_type` = `score` | 117 | **76** (the sum is over 100, then cut to 100) |
| `reasons[]` ordered by points, highest first | 90 | **103** (ordered by primary anomaly type first, then points) |

Examples:
- **`A-P02588`, score 97.** Its reasons are behaviour_change 30 + 25 + 12, peer_deviation 37 and multivariate_outlier 10, which add up to **114**. Behaviour change is capped from 67 to 50, so 50 + 37 + 10 = 97.
- **`A-P03247`, score 100.** Its reasons add up to **193**, and its capped `points_by_type` still adds up to 167.

`docs/API.md` on the backend branch says `points_by_type` "sum to the score (capped at 100)". That is only true before the final 100 cap.

### Sorting and pagination of `GET /alerts`

| | Contract | Backend |
|---|---|---|
| Default order | `risk_score` descending | `-score` (score descending, ties by `rank` ascending). Also `score`, `rank`, `player_id`, with a `-` prefix for descending. Anything else gives 400 |
| Pagination | none (the whole list) | `limit` (default **50**, max 1000) and `offset`. `total` gives the full count (193 in the committed data) |
| Filters | `band`, `type`, `status`, `q` (optional) | `band`, `team`, `type`, `status`, `q`, `min_score`. Comma-separated, case-insensitive. `q` searches player ID, occupation, region and reason codes |
| Default status filter | The mock's chip says "Status: Open" | No default. `/alerts` returns **every** status unless `status=open` is passed |

If the live frontend calls `/alerts` without `limit`, it shows only the top 50 of 193.

---

## Practical checks

All from source, not verified live.

| Item | Finding |
|---|---|
| **Base URL and port** | `http://127.0.0.1:8000`. Started with `uvicorn backend.app.main:app --reload` or `.\run_demo.ps1` from the repo root (both on `origin/backend`). Swagger UI is at `/docs` and the schema at `/openapi.json`. |
| **Before it serves data** | Run the pipeline first with `python -m backend.pipeline.run_all` (about 1.5 minutes). Until then, every data endpoint returns **503** with `{"detail":"… Run the pipeline first …"}`, while `/health` and `/docs` still work. The live frontend needs a visible 503 state. |
| **Python** | The backend README says it was "tested with Python 3.13". The docs still list 3.11 as only a suggestion (HANDOFF open item #4). Python is not installed on this machine. |
| **CORS** | `CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])`. A browser can call it from `file://` (which sends `Origin: null`) or from any local server, without credentials. |
| **CORS gap** | Every response carries `X-Data-Source: synthetic`, but CORS does not expose it (`expose_headers` is not set). A frontend on a different origin **cannot read that header**. Use `/stats` → `synthetic: true` or `/meta` → `synthetic: true` instead. |
| **`run_demo.ps1`** | Prints "Dashboard: open frontend/index.html", but the backend branch has no `frontend/index.html`. |
| **Action endpoints** | `POST /alerts/{alert_id}/decision`, body `{"decision": "accept" \| "escalate" \| "close", "note": "", "reason": null, "investigator": null}`. Returns **201** with the stored decision and the new `status`. `close` without `reason` or `note` gives **422**. Unknown alert gives **404**. |
| **Escalate button** | `decision: "escalate"` → status `escalated`. **Exists.** |
| **Dismiss button** | `decision: "close"` plus a required `reason` → status `closed`. **Exists**, but the UI must ask for a reason. |
| **Request info button** | **No endpoint, decision value or status for this.** |
| **Primary "recommended action" button** | `decision: "accept"` → status `accepted`. **Exists.** |
| **"Override with reason" button** | No separate decision. The nearest is `close` with a `reason`, or `escalate` with a `note`. |
| **Decision history** | `GET /alerts/{alert_id}/decisions` (oldest first). `GET /alerts/{alert_id}/report` returns a Markdown case summary. |
| **Keys** | Every action and alert endpoint uses `alert_id` (`A-P…`), while player endpoints use `player_id`. The frontend must keep both. |
| **Calls per dossier** | Up to 5 (`/alerts/{id}`, `/players/{id}/peers`, `/players/{id}/network`, `/players/{id}/transactions`, `/players/{id}`), versus 1 in the contract. |
| **Calls per queue** | 1 `/alerts` call. The heat strip would need 1 extra transactions call **per row** (50 per page). |

---

## Proposed resolutions

Each difference gets one of four resolutions:
- **Adapter:** a mapping function in the live frontend;
- **Redesign:** change the component to use what exists;
- **Not available:** show "Not available";
- **Backend add:** ask the backend developer.

"Backend decides" marks items the backend developer must decide before the frontend can finish.

| # | Difference | Resolution | Backend decides? |
|---|---|---|---|
| R1 | **Two backends on two branches** (`backend`, `wireframe`) with different enums and endpoints | Agree on one before building `index.html`. This document assumes `origin/backend`. | **Yes** (team) |
| R2 | **Reason points don't add up to the score** (121/193) | **Backend add, preferred:** add a per-reason `contribution` (points after the per-type and total caps, which do add up to `score`) next to `points`. **Fallback redesign:** show `+points` per reason and replace the sum line with "Raw evidence points 114 · capped at 50 per type and 100 total → score 97", using `points_by_type` and `raw_points`. Never print a false "=" | **Yes** |
| R3 | **4 bands vs 3** (`Critical` 90–100) | **Backend decides** whether Critical stays. If it stays: the adapter lowercases the band, maps `critical` to the High colour and label "Critical", and lights the 4th meter bar (the mock already does this at 90+). Update DESIGN.md, PRODUCT.md and API_CONTRACT.md to match, or change `BANDS` in `common.py` | **Yes** |
| R4 | **No Low alerts** (`ALERT_MIN_SCORE` 40) | **Redesign:** remove Low from the queue ribbon and band filter, or label it "Low (below alert threshold): not queued". Keep the Low colour for network nodes and `/players/{id}`, which can be Low | No |
| R5 | `risk_score` → `score`, `headline` → `title`, `evidence` → `detail`, `weight` → `points`, `type` → `anomaly_type`, `recommended_action.label` → `.action`, `top_reason` → `top_reason_title`, `alerts` → `items`, profile fields nested under `profile` | **Adapter:** one `toViewModel(alert, peers, network, txns)` function that returns the mock's player shape, so the mock's rendering code is reused unchanged | No |
| R6 | Anomaly type names (`location_anomaly`, `linked_players`) plus 2 new types (`cash_cycling`, `multivariate_outlier`) | **Adapter:** extend `TYPE_LABEL` with "Location anomaly", "Linked players", "Cash in / cash out" and "Model outlier". **Redesign:** consider hiding `multivariate_outlier` from the type tags, because it is on 176 of 193 alerts and adds noise | No |
| R7 | **Status values differ.** No `in_review` or `awaiting_info`; `accepted` is new | **Adapter:** `open` → "New", `accepted` → "Accepted", `escalated` → "Escalated", `closed` → "Dismissed" (or "Closed"). **Backend decides** whether to add `in_review` and `awaiting_info` (see R8) | **Yes** |
| R8 | **No "Request info" action** | **Backend add:** a `request_info` decision that sets status `awaiting_info`. Until then, hide the button or show it disabled with "Not available yet" | **Yes** |
| R9 | "Override with reason" has no decision of its own | **Redesign:** make it open a reason field that submits `close` (dismiss) or `escalate` with `reason` and `note`. Also show the existing `latest_decision` and `/decisions` history in the dossier | No |
| R10 | `initials` missing (no names in the backend) | **Redesign:** replace the avatar with a team mark (AML / FR / SG from `team`) or drop it. Don't make up initials | No |
| R11 | `age` missing; `age_band` exists | **Redesign:** show "18–24 yrs". This closes HANDOFF open item #15 in favour of the band | No |
| R12 | `province` missing; `home_region` exists | **Redesign:** show "Home region: Toronto/GTA". **Adapter:** decide in/out of province by checking whether a region is one of the 5 Ontario regions. HANDOFF open item #15 can drop `province` | No |
| R13 | `income_band` values differ (`"<20k"` vs `"Under $25k"`) | **Adapter:** display map (`"<20k"` → "Under $20k", `"20-40k"` → "$20k–$40k", and so on) | No |
| R14 | `activity_30d` missing (dossier chart) | **Adapter, short term:** fetch `/players/{id}/transactions?type=bet&since=<current_start>&limit=2000` and sum `amount_cad` per day into 30 values. Take `current_start` from `/players/{id}/timeline`. **Backend add, better:** an `activity_30d` array on `/alerts/{id}` | **Yes** (whether to add it) |
| R15 | `activity_30d` missing (queue heat strip) | **Backend add:** `activity_30d` on `/alerts` rows. Otherwise **redesign** the strip from fields the row already has, or remove it. Do not make 50 extra calls per page | **Yes** |
| R16 | Activity chart dates are hardcoded (Sep 15 → Oct 14) | **Adapter:** build the axis from `current_start` and `reference_date` (real window 2026-09-01 to 2026-09-30) | No |
| R17 | `locations[]` missing | **Adapter:** group `ip_region` from the 30-day transactions and count them. The label is "Transactions by region", not "Sessions", because the backend counts transactions. **Backend add, optional:** a `locations` array on `/alerts/{id}` | No |
| R18 | Peer comparison spread over `/players/{id}/peers` | **Adapter:** take the `deposits_30d` row for `monthly_spend`, `peer_median` and `peer_p90`. **Redesign, optional:** the endpoint gives 6 features plus `own_baseline`, IQR and `z_score`, enough to show the player's history alongside peers (PRODUCT requirement #2 asks for both) | No |
| R19 | `peer_median` can be 0, `null` or below $100 | **Adapter:** guard the ratio (show "n/a" when the median is 0 or `null`). **Redesign:** let the peer chart's lower bound follow the data instead of a fixed $100 | No |
| R20 | `linked_players[]` is a graph, not a list | **Adapter:** keep edges where `source` or `target` is the focus player. Build `link` from `shared[]` ("Shared device DEV-ULC2FSQH · shared payment method PM-TJC0T1SK") and add "· N opposite bets" when `opposite_bets` > 0. Take each badge from the node's `score` and `band`. Show `summary` as the caption | No |
| R21 | No `GET /summary`; no `as_of` time; no `monitoring` | **Adapter:** `/stats` → `alerts`, `by_status.open`, `by_band`. Show "Data as of 2026-10-01" from `reference_date`. Derive `monitoring` from `/health` (ok → "Connected", failure → "Offline"). **Backend add:** a `scored_at` timestamp written by `detect.py` if a real "last scan" time is wanted | **Yes** (`scored_at`) |
| R22 | `/stats.by_band` counts every status, but the ribbon says "open alerts" | **Adapter:** count bands from `/alerts?status=open&limit=1000`. **Backend add, cleaner:** `by_band_open` on `/stats` | **Yes** (whether to add it) |
| R23 | `/alerts` returns 50 by default, all statuses | **Adapter:** call `/alerts?status=open&limit=1000` (or page with `offset`), and show `total` | No |
| R24 | Alert vs player keys | **Adapter:** keep `alert_id` on each queue row, call `/alerts/{alert_id}` for the dossier and actions, and use `player_id` for player endpoints | No |
| R25 | Case number drops a digit with `slice(2)` | **Adapter:** `"SNT-2026-" + player_id.slice(1)`, or use `alert_id` directly | No |
| R26 | Reasons ordered by primary type first, not by points | **Redesign:** keep the backend order (it matches the assigned team), and change the sub-heading from "strongest reason first" to "primary concern first" | **Yes** (confirm the order is intended) |
| R27 | `recommended_action.rationale` is generic per type | **Not available** as player-specific text. Show the generic rationale plus `summary`, which does carry this player's numbers. Show `secondary[]` as "Also: …" lines | No |
| R28 | `X-Data-Source` header unreadable cross-origin | **Adapter:** use `synthetic: true` from `/stats`. **Backend add, optional:** `expose_headers=["X-Data-Source"]` | No |
| R29 | Transaction `timestamp` has no timezone | **Adapter:** treat it as local Toronto time for display. **Backend decides:** confirm or add an offset | **Yes** |
| R30 | API returns 503 before the pipeline runs | **Redesign:** a visible empty state: "No data yet. Run `python -m backend.pipeline.run_all`" | No |

---

## Questions for the backend developer

1. **Which backend is the real one: `origin/backend` or `origin/wireframe`?** The two have different status values, decisions and endpoints, and `wireframe` already has its own `frontend/index.html`. The live frontend can only target one.
2. **Reason points vs. score:** can you add a per-reason `contribution` (after the 50-per-type and 100-total caps) that adds up exactly to `score`? Otherwise, are you happy for the UI to show raw points plus a "capped" explanation instead of "points total = score"?
3. **Bands:** keep `Critical` (90–100) or move to the 3 bands in the docs? Today 100 of 193 alerts are Critical and 79 score exactly 100. Is that the intended distribution, or should the caps or weights be re-tuned so the top of the queue spreads out?
4. **Statuses:** will you add `request_info` → `awaiting_info`, and an `in_review` state (for example, set when an investigator opens or claims a case)? Or should the UI drop "Request info" and "In review"?
5. **Daily activity:** can `/alerts` rows and `/alerts/{id}` include `activity_30d` (30 daily wagered totals, oldest first)? Without it, the queue heat strip has to go.
6. **Scan time:** can `detect.py` record a `scored_at` timestamp (ISO with offset) and `/stats` return it, so "last scan" and "Monitoring: stale" can be real? What age should count as stale (HANDOFF open item #16)?
7. **Open counts:** should `/stats.by_band` count only open alerts, or can you add `by_band_open`?
8. **Reason order:** is "primary anomaly type first, then points" intended (103 of 193 alerts are not in points order)?
9. **Locations:** is it fine for the frontend to count `ip_region` from transactions, or will you add a `locations` summary to `/alerts/{id}`?
10. **Timezone:** transaction `timestamp` has no offset. Is it Toronto local time?
11. **Docs drift on the backend branch:**
    - `backend/README.md` and `docs/API.md` say peer z ≥ 3, but `detect.py` uses `z_threshold: 2.5`;
    - `docs/API.md` shows `total: 190`, but the committed data has 193;
    - `/meta` and the `type` filter list `linked_ring`, which never appears on an alert;
    - `recommended_action.primary_type` is returned but not declared in `schemas.py`.

    Which numbers are current?
12. **Committed data:** `data/scores/alerts.json` and `validation_report.json` are committed on the backend branch, because `.gitignore` only ignores `*.csv` and `*.parquet`. Is that on purpose, as a demo fallback?
