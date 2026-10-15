# API Reference

FastAPI service in `backend/app/`. Start it from the repo root:

```bash
uvicorn backend.app.main:app --reload
```

- Base URL: `http://127.0.0.1:8000`
- Interactive docs (try every call in the browser): `http://127.0.0.1:8000/docs`
- CORS is open, so `frontend/index.html` can call it from `file://` or `python -m http.server`.
- Every response carries the header `X-Data-Source: synthetic`.
- If the pipeline has not been run, data endpoints return **503** with a message telling you to run `python -m backend.pipeline.run_all`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` |
| GET | `/meta` | Bands, teams, anomaly types, action catalogue, weights (for filters and legends) |
| GET | `/stats` | Queue counts by band / team / type / status, score histogram, reference date |
| GET | `/validation` | Detection quality report (recall, precision@k, rule hit rates) |
| GET | `/alerts` | Ranked alert queue (summary rows), filterable and paginated |
| GET | `/alerts/export.csv` | Whole queue as CSV with current status |
| GET | `/alerts/{alert_id}` | Full alert: reasons, evidence, comparisons, recommended action, latest decision |
| POST | `/alerts/{alert_id}/decision` | Record `accept` / `escalate` / `close` with a note |
| GET | `/alerts/{alert_id}/decisions` | Decision audit trail, oldest first |
| GET | `/alerts/{alert_id}/report` | Printable Markdown case summary |
| GET | `/players/{player_id}` | Profile, score, every computed feature, recent transactions |
| GET | `/players/{player_id}/transactions` | Paginated transaction history (`type`, `since`, `limit`, `offset`) |
| GET | `/players/{player_id}/peers` | Player vs own baseline vs peer distribution, per feature (peer chart) |
| GET | `/players/{player_id}/timeline` | Weekly series tagged `baseline` / `current` (behaviour-over-time chart) |
| GET | `/players/{player_id}/network` | Linked players within `hops` (default 2): nodes + edges (network graph) |
| GET | `/network/clusters` | All linked-player clusters of size >= `min_size`, highest risk first |

IDs: alerts are `A-<player_id>` (e.g. `A-P00066`); players are `P00001`–`P05000`.

## `GET /alerts`

Query parameters (all optional; comma-separated values mean "any of"):

| Param | Example | Notes |
|---|---|---|
| `band` | `Critical,High` | case-insensitive |
| `team` | `Fraud` | `AML`, `Fraud`, `Safer Gambling` |
| `type` | `location_anomaly` | any anomaly type in the alert's `anomaly_types` |
| `status` | `open` | `open`, `accepted`, `escalated`, `closed` |
| `q` | `P0012` / `Student` / `IMPOSSIBLE` | searches player ID, occupation, region, reason codes |
| `min_score` | `70` | |
| `sort` | `-score` | `score`, `-score` (default), `rank`, `player_id` (prefix `-` for descending) |
| `limit`, `offset` | `50`, `0` | max limit 1000 |

```json
{
 "total": 190, "limit": 1, "offset": 0,
 "items": [{
   "alert_id": "A-P03493", "player_id": "P03493", "rank": 1, "score": 100, "band": "Critical", "team": "AML",
   "anomaly_types": ["linked_players", "income_mismatch", "behaviour_change", "peer_deviation", "multivariate_outlier"],
   "top_reason_code": "OPPOSITE_BETTING_LINKED", "top_reason_title": "Betting against linked accounts",
   "reason_count": 7, "status": "open",
   "profile": {"age_band": "35-44", "occupation": "...", "income_band": "<20k", "home_region": "Southwestern Ontario", "signup_date": "2025-12-25"},
   "recommended_action": "Open a linked-account investigation", "created_at": "2026-10-01"
 }]
}
```

## `GET /alerts/{alert_id}`

The full alert object. `frontend/mock/alerts.json` contains five real examples in exactly this shape (one per primary anomaly type), so the dashboard can be built without the API.

Key fields:

- `score` (0–100), `band`, `rank`, `team`
- `points_by_type`: points per anomaly type after the per-type cap; they sum to the score (capped at 100)
- `raw_points`: total before caps (used to break ties at 100)
- `reasons[]`: ordered with the primary anomaly type first. Each reason has:
  - `code`, `anomaly_type`, `title`, `points`
  - `detail`: a plain-language sentence built only from the evidence values
  - `evidence`: the computed numbers behind it
  - `comparison`: `peer_median` and `own_baseline` (either may be `null` when not meaningful)
- `recommended_action`: `{action, team, rationale, secondary: [{team, action}], primary_type}`
- `summary`: two-sentence template summary (restates evidence only)
- `key_metrics`: deposits / withdrawals / staked / net loss / bets / avg stake (30 days), usual deposits, income estimate
- `latest_decision`: `null` or the most recent decision

## `POST /alerts/{alert_id}/decision`

```json
{"decision": "close", "reason": "benign household", "note": "Spouses sharing a tablet; stakes small", "investigator": "J. Doe"}
```

- `decision`: `accept` -> status `accepted`, `escalate` -> `escalated`, `close` -> `closed`
- `close` requires a `reason` or `note` (422 otherwise): every override is recorded with a reason
- Returns 201 with the stored decision and the new `status`. Decisions persist in `data/decisions.db` (SQLite, git-ignored).

## `GET /players/{player_id}/peers`

```json
{"player_id": "P00066", "peer_group": "18-24 | 20-40k", "peer_group_size": 65, "z_threshold": 3.0,
 "features": [{"feature": "deposits_30d", "label": "deposits (30 days)", "value": 5370.0, "own_baseline": 2543.33,
               "peer_median": 20.0, "peer_q1": 20.0, "peer_q3": 50.0, "peer_p90": 90.0,
               "z_score": 8.43, "percentile": 1.0, "flagged": true}, "..."]}
```

Suggested chart: one row per feature with the peer IQR as a bar, the peer median as a tick, the player as a dot and the own baseline as a hollow marker.

## `GET /players/{player_id}/timeline`

```json
{"player_id": "P00066", "reference_date": "2026-10-01", "current_start": "2026-09-01", "baseline_start": "2026-06-03",
 "weeks": [{"week_start": "2026-09-28", "deposits": 0.0, "withdrawals": 0.0, "staked": 451.67, "payouts": 0.0,
            "net_loss": 451.67, "bets": 2, "night_share": 1.0, "regions": ["Northern Ontario"], "window": "current"}]}
```

## `GET /players/{player_id}/network`

```json
{"player_id": "P00118", "cluster_size": 5, "cluster_avg_score": 100.0,
 "summary": "Directly linked to 4 player(s) through shared device; cluster of 5 players, 4 other(s) also on the alert queue. 10 bet(s) on opposite sides of the same events as linked players.",
 "nodes": [{"id": "P00118", "score": 100, "band": "Critical", "is_focus": true, "alert_id": "A-P00118"}],
 "edges": [{"source": "P02844", "target": "P01662", "opposite_bets": 3,
            "shared": [{"type": "device", "value": "DEV-ULC2FSQH"}, {"type": "payment_method", "value": "PM-TJC0T1SK"}]}]}
```

## Reason codes

| Code | Anomaly type | Team | Fires when |
|---|---|---|---|
| `INCOME_MISMATCH` | income_mismatch | AML | 30-day deposits >= 0.5x estimated monthly income (and >= $500) |
| `CASH_IN_CASH_OUT` | cash_cycling | AML | >= 60% of deposits withdrawn while staking < 100% of deposits (deposits >= $1,000) |
| `PEER_DEVIATION` | peer_deviation | AML / Safer Gambling | robust z >= 3 within peer group on a material amount |
| `IMPOSSIBLE_TRAVEL` | location_anomaly | Fraud | consecutive transactions imply travel > 900 km/h |
| `UNEXPECTED_LOCATION` | location_anomaly | Fraud | >= 15% of activity outside home region (+8 if outside Canada) |
| `NEW_DEVICE_AWAY` | location_anomaly | Fraud | a new device this month plus out-of-region activity |
| `NEW_DEVICE_NEW_PAYOUT` | location_anomaly | Fraud | withdrawal to a payment method first seen this month, with a new device |
| `DEPOSIT_SPIKE` | behaviour_change | Safer Gambling | deposits >= 3x own 30-day baseline (and >= $300) |
| `LOSS_CHASING` | behaviour_change | Safer Gambling | >= 3 deposits within 15 min of a losing bet |
| `LATE_NIGHT_SHIFT` | behaviour_change | Safer Gambling | night-bet share up >= 20 points (>= 10 bets) |
| `STAKE_ESCALATION` | behaviour_change | Safer Gambling | average stake >= 3x own baseline |
| `OPPOSITE_BETTING_LINKED` | linked_players | AML | >= 3 bets on the opposite side of an event from a linked account |
| `LINKED_PLAYERS` | linked_players | AML | shares identifiers with >= 2 other players |
| `MODEL_OUTLIER` | multivariate_outlier | AML | Isolation Forest percentile >= 95% |

Thresholds and points live in `backend/pipeline/detect.py` (`WEIGHTS` and the rule functions); band cut-offs in `backend/pipeline/common.py`.
