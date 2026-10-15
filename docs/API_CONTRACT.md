# API Contract: what the dashboard needs from the backend

**For:** the backend developer (build steps 3–5 in [WORKFLOW.md](WORKFLOW.md)).
**Visual reference:** `frontend/mock_frontend.html`. Double-click it to open. It is a **static mock** with 8 hardcoded fictional players. The real, live frontend will be a separate `frontend/index.html`, built later in step 6. It will call the endpoints below and display exactly these fields.

Everything here is a proposal. Field names match the mock's hardcoded data, so the live frontend can swap that data for API calls with minimal change.

## Conventions

- JSON, `snake_case` field names.
- Money is a number in **Canadian dollars**, with no currency symbol (`14850`, not `"$14,850"`). The frontend formats it.
- Dates and times are ISO 8601 in Toronto time (`2026-10-14T14:32:00-04:00`).
- Enums are lowercase strings. The frontend turns them into labels: `behaviour_change` → "Behaviour change", `in_review` → "In review".
- **Risk bands (3):** `low` 0–39 · `medium` 40–69 · `high` 70–100. These cut-offs are a draft until validation (step 4).
- ⚙ marks a field the backend must **compute** (more than a lookup or a simple sum). Those are the fields that need real work in `detect.py` / `build_features.py`.

> The mock stores status as a display label (`"In review"`). The API should send the enum (`"in_review"`), and the live frontend will map it.

## Fields the mock displays

### Player and alert

| Field | Type | Example | Where it appears | Supplied by |
|---|---|---|---|---|
| `player_id` | string | `"P-10482"` | Queue row, dossier title, case number, linked-players list | `players.csv` |
| `initials` | string (2 chars) | `"MR"` | Avatar circle in the queue and linked list | Generated with the synthetic player (`generate_data.py`). No real names anywhere |
| `age` | integer | `24` | Dossier header meta line | `players.csv`. **Note:** step 1 currently plans `age_band`. Either add exact `age` or show the band here |
| `occupation` | string | `"Student, part-time retail"` | Dossier header | `players.csv` |
| `income_band` | string | `"Under $25k"` | Dossier header | `players.csv` |
| `province` | string (2-letter code) | `"ON"` | Dossier header. Also decides "In province / Outside province" on locations | `players.csv` (add next to `home_region`) |
| `risk_score` | integer 0–100 | `91` | Queue badge, score ring, sum line under "Why flagged" | ⚙ `detect.py`: combined score |
| `band` | enum `low` / `medium` / `high` | `"high"` | Badge colour and label, ring colour, ribbon counts | ⚙ `detect.py`: from `risk_score` using the band cut-offs |
| `anomaly_types` | array of enum `income_mismatch` / `peer_deviation` / `location` / `behaviour_change` | `["income_mismatch","peer_deviation"]` | Tags under the score ring | ⚙ `detect.py`: the distinct `type`s of the reasons, excluding `network` |
| `status` | enum `new` / `in_review` / `awaiting_info` / `escalated` / `dismissed` | `"escalated"` | Queue row tag, rubber stamp in the dossier header | Decision store (local JSON/SQLite) or Jube case. Default `new` |
| `recommended_action.label` | string | `"Request source of funds"` | "Recommended action" heading text | ⚙ `detect.py`: mapping from the top reason code(s) |
| `recommended_action.team` | enum `AML` / `Fraud` / `Safer Gambling` | `"AML"` | Under the action | ⚙ same mapping |
| `recommended_action.rationale` | string, 1–2 sentences | `"Deposits far exceed…"` | Under the action | ⚙ same mapping, filled with this player's facts |

### Reasons (`reasons[]`, the "Why flagged" evidence thread)

Order the reasons by `weight`, highest first. **The weights must add up to `risk_score`.** The mock prints "points total 91 = risk score 91", so the backend has to produce a score that splits cleanly into per-reason points.

| Field | Type | Example | Where it appears | Supplied by |
|---|---|---|---|---|
| `type` | enum: the 4 anomaly types + `network` | `"income_mismatch"` | Small uppercase label on each reason card | ⚙ `detect.py`: the rule or detector that fired |
| `headline` | string, ≤ 60 chars | `"Deposits are 7× declared monthly income"` | Reason card title; the first reason is also the one-line summary in the queue row | ⚙ template per reason code, filled with computed numbers |
| `evidence` | string, 1 sentence with the actual numbers | `"$14,850 deposited in 30 days against an income band under $25k a year (about $2,080 a month)."` | Reason card body | ⚙ template per reason code. Must contain only computed values |
| `weight` | integer (points) | `36` | "+36 points" and the bar on the card | ⚙ `detect.py`: this reason's contribution to the score |

### Peer comparison ("Compared with peers")

| Field | Type | Example | Where it appears | Supplied by |
|---|---|---|---|---|
| `monthly_spend` | number (CAD) | `14850` | Player diamond on the strip plot; the ratio figures | `build_features.py`: `deposits_30d` |
| `peer_median` | number (CAD) | `310` | Solid tick on the strip plot, legend | ⚙ `peer_stats.parquet`: median `deposits_30d` of the player's peer group |
| `peer_p90` | number (CAD) | `1120` | Dashed tick, end of the shaded "90% of peers" range, legend | ⚙ `peer_stats.parquet`: 90th percentile of the same |

### History, locations, network

| Field | Type | Example | Where it appears | Supplied by |
|---|---|---|---|---|
| `activity_30d` | array of exactly 30 numbers (CAD), oldest first, the last item being the `as_of` day | `[120, 0, 340, …, 980]` | 30-day heat strip in each queue row; bar chart in "30-day activity" | `transactions.csv`: sum of `bet` amounts per day |
| `locations[]` | array of `{region, count}`, largest first | `[{"region":"Toronto, ON","count":171}]` | "Locations" list with bars and the In/Outside province flag | `transactions.csv`: sessions grouped by `ip_region`. The region string must end in `, <province code>` for Canadian regions so the in-province check works |
| `linked_players[]` | array of `{player_id, link}` | `[{"player_id":"P-20917","link":"Shared device D-7F31 · shared card ending 4417"}]` | "Linked players" list. The frontend looks up each linked player's badge from the alert list | ⚙ network analysis (step 7, `networkx`). Send `[]` until it is built; the mock shows an empty state |

### Summary (header and ribbon)

| Field | Type | Example | Where it appears | Supplied by |
|---|---|---|---|---|
| `as_of` | ISO datetime | `"2026-10-14T14:32:00-04:00"` | "last scan 2026-10-14 14:32" next to Monitoring | Time the scoring batch ran |
| `monitoring` | enum `active` / `stale` / `offline` | `"active"` | Pulsing "Monitoring" indicator (the mock always shows active) | API: `stale` if `as_of` is older than a threshold (TBD) |
| `open_alerts` | integer | `8` | "8 open alerts" in the ribbon | Count of alerts whose status is not `dismissed` |
| `by_band` | object `{high, medium, low}` | `{"high":3,"medium":3,"low":2}` | Band counts and the proportion bar in the ribbon | Count of open alerts per band |

### Calculated by the frontend (the backend does not need to send these)

- **Case number** `Case SNT-2026-10482` (from `player_id`).
- **Meter segments**: `ceil(risk_score / 25)` of 4 bars are filled.
- **Ratios**: "47.9× the peer median" and "13.3× the peer 90th percentile".
- **Activity figures**: the first-half daily average (dashed line) and the last-7-days total.
- **Location flag**: "In province / Outside province".

## Endpoints

### `GET /summary`

Header and ribbon data.

```json
{
  "as_of": "2026-10-14T14:32:00-04:00",
  "monitoring": "active",
  "open_alerts": 8,
  "by_band": { "high": 3, "medium": 3, "low": 2 }
}
```

### `GET /alerts`

The ranked queue. Return it sorted by `risk_score`, descending. It only carries what a queue row shows. Optional query parameters for the live version: `band`, `type`, `status`, `q` (search). The mock's filters are placeholders, so the API may ignore them at first.

```json
{
  "as_of": "2026-10-14T14:32:00-04:00",
  "alerts": [
    {
      "player_id": "P-10482",
      "initials": "MR",
      "risk_score": 91,
      "band": "high",
      "status": "escalated",
      "top_reason": "Deposits are 7× declared monthly income",
      "anomaly_types": ["income_mismatch", "peer_deviation", "behaviour_change"],
      "activity_30d": [120,0,340,80,510,0,620,900,450,1200,0,780,640,1500,300,980,410,0,1350,720,560,1900,880,430,1100,0,1650,760,1240,980]
    },
    {
      "player_id": "P-20917",
      "initials": "DK",
      "risk_score": 84,
      "band": "high",
      "status": "in_review",
      "top_reason": "Bets placed from Malta on an Ontario account",
      "anomaly_types": ["location", "peer_deviation"],
      "activity_30d": [60,0,0,140,210,0,90,380,0,520,640,0,300,710,880,0,450,960,0,1200,350,0,820,1100,460,0,980,1300,0,740]
    }
  ]
}
```

`top_reason` is `reasons[0].headline`, sent here so the queue doesn't need a full player fetch per row.

### `GET /players/{player_id}`

Everything the dossier shows for one player. `404` with `{"detail": "Player not found"}` for an unknown ID.

```json
{
  "player_id": "P-10482",
  "initials": "MR",
  "age": 24,
  "occupation": "Student, part-time retail",
  "income_band": "Under $25k",
  "province": "ON",
  "risk_score": 91,
  "band": "high",
  "anomaly_types": ["income_mismatch", "peer_deviation", "behaviour_change"],
  "status": "escalated",
  "reasons": [
    { "type": "income_mismatch", "headline": "Deposits are 7× declared monthly income",
      "evidence": "$14,850 deposited in 30 days against an income band under $25k a year (about $2,080 a month).", "weight": 36 },
    { "type": "peer_deviation", "headline": "Spend is 48× the peer median",
      "evidence": "$14,850 vs. peer median $310 for students aged 18–24 earning under $25k.", "weight": 29 },
    { "type": "network", "headline": "Shares a device and payment card with P-20917",
      "evidence": "Device D-7F31 and card ending 4417 used on both accounts in the last 30 days.", "weight": 18 },
    { "type": "behaviour_change", "headline": "Deposits up 6× on own 90-day baseline",
      "evidence": "$14,850 this month vs. $2,410 a month on average over the previous 90 days.", "weight": 8 }
  ],
  "monthly_spend": 14850,
  "peer_median": 310,
  "peer_p90": 1120,
  "activity_30d": [120,0,340,80,510,0,620,900,450,1200,0,780,640,1500,300,980,410,0,1350,720,560,1900,880,430,1100,0,1650,760,1240,980],
  "locations": [
    { "region": "Toronto, ON", "count": 171 },
    { "region": "Mississauga, ON", "count": 15 }
  ],
  "linked_players": [
    { "player_id": "P-20917", "link": "Shared device D-7F31 · shared card ending 4417" }
  ],
  "recommended_action": {
    "label": "Request source of funds",
    "team": "AML",
    "rationale": "Deposits far exceed what the declared income supports, and the account shares a device and card with another high-risk player."
  }
}
```

## Relation to the earlier endpoint draft

[WORKFLOW.md](WORKFLOW.md) step 5 drafted more endpoints: `/alerts/{id}`, `/players/{id}/peers`, `/players/{id}/network`, `POST /alerts/{id}/decision` and `/health`.

- **For the mock:** the three endpoints above are enough. Peer and network data are folded into `GET /players/{id}`.
- **Decision endpoint:** `POST /alerts/{id}/decision` is still needed once the Escalate / Request info / Dismiss buttons become real. Its result sets `status`.
- **Health check:** `GET /health` is still useful for the demo.

## Checklist for the backend developer

- [ ] Reason `weight`s add up to `risk_score` for every player.
- [ ] Every reason has a `headline` and an `evidence` sentence containing the real computed numbers.
- [ ] `activity_30d` always has exactly 30 values.
- [ ] Canadian `locations[].region` values end in `, XX` (province code).
- [ ] `band` matches the cut-offs: low 0–39, medium 40–69, high 70–100.
- [ ] `linked_players` is `[]`, never missing, when there are no links.
- [ ] All data is synthetic, and no real names appear anywhere.
