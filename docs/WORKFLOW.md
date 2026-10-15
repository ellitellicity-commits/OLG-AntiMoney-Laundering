# Build Workflow

Build in this order. Each step reads the previous step's output files, so the steps can be tested independently. File paths are relative to the repo root.

Owners are placeholders. Team members and roles haven't been provided yet, so every `Owner` line is **TBD**. Fill in one owner per step once the team is known (see the Open items list in [HANDOFF.md](HANDOFF.md)).

```
1 Synthetic data → 2 Features → 3 Detection → 4 Validation → 5 API → 6 Dashboard → 7 Bonus → 8 Demo
```

Steps 5 (API) and 6 (Dashboard) can start in parallel once step 3 has produced a sample `risk_scores.csv`. Step 6 can begin against a hand-written mock JSON file.

---

## Step 1 — Synthetic data

**What to build:** a seeded, reproducible generator of sports-betting players and transactions, with risky behaviour injected for a known subset of players.

**Inputs:** a config block at the top of the script (random seed, number of players, date range, injection rates). Suggested starting values: 5,000 players, 180 days, 3–5% risky players. These are **TBD** and can be adjusted.

**Outputs:**
| File | Contents (minimum columns) |
|---|---|
| `data/synthetic/players.csv` | `player_id, age_band, occupation, income_band, home_region, signup_date` |
| `data/synthetic/transactions.csv` | `txn_id, player_id, timestamp, type (deposit / withdrawal / bet / payout), amount_cad, sport, market, odds, channel (web / app / retail), device_id, ip_region, payment_method_id` |
| `data/synthetic/linked_identifiers.csv` | `player_id, identifier_type (device / payment_method / address), identifier_value`, used for network analysis |
| `data/synthetic/scenario_labels.csv` | `player_id, scenario, start_date, end_date`: the ground truth for validation |

**Scenarios to inject (one label each):** `income_mismatch`, `peer_deviation`, `location_anomaly`, `behaviour_change`. Stretch: `linked_ring` (several accounts sharing devices/payment methods and moving money between them).

**Tool / library:** Python, `numpy`, `pandas`, `Faker` (for occupations/regions only; no realistic personal names needed).

**Script:** `backend/pipeline/generate_data.py`

**Owner:** TBD

**Done when:** running the script twice with the same seed produces identical files; every scenario has at least 20 labelled players; normal players look plausible (spend roughly in line with income band); and nothing in the data is real.

---

## Step 2 — Features

**What to build:** per-player features for a current window (last 30 days) compared with a baseline window (prior 90 days), plus peer-group statistics.

**Peer group (draft, TBD):** `age_band × income_band × home_region`. Merge small groups (< 30 players) into the next broader group.

**Example features:**
- Spend vs income: `deposits_30d / monthly_income_estimate`
- Peer deviation: z-score of `deposits_30d`, `avg_stake`, `bets_per_day`, `net_loss_30d` within the peer group
- Location: `distinct_ip_regions_30d`, `share_of_txns_outside_home_region`, `impossible_travel_count`
- Behaviour change: `deposits_30d / deposits_baseline`, change in `avg_stake`, change in betting hours (e.g. night share)
- AML pattern: `withdrawal_to_deposit_ratio` with low `bet_turnover` (money in and out without real betting)
- Network: `shared_identifier_count`

**Inputs:** the step 1 files.

**Outputs:** `data/features/player_features.parquet` (one row per player) and `data/features/peer_stats.parquet` (median, IQR, mean and std per peer group per feature).

**Tool / library:** `pandas`, `pyarrow`.

**Script:** `backend/pipeline/build_features.py`

**Owner:** TBD

**Done when:** every player has one row with no unexpected nulls, the feature list is written in a docstring with a one-line definition each, and injected players visibly stand out on their scenario's feature (quick check in a notebook).

---

## Step 3 — Detection and scoring

**What to build:** three detectors combined into one explainable 0–100 risk score.

1. **Rules:** clear thresholds per anomaly type (e.g. deposits > 5× monthly income estimate). Each rule emits a reason code.
2. **Peer z-scores:** flag features with |z| above a threshold (draft 3, TBD) within the peer group.
3. **Isolation Forest:** overall unusualness across all features.

**Score combination:** weighted sum normalised to 0–100. Weights are **TBD** and get tuned in step 4.

**Reason format** (every flag must produce one):
```json
{"code": "INCOME_MISMATCH", "anomaly_type": "income_mismatch",
 "title": "Deposits far above declared income",
 "evidence": {"deposits_30d": 18400, "income_band": "40-60k"},
 "comparison": {"peer_median": 620, "own_baseline": 540},
 "points": 28}
```

**Recommended action:** a fixed mapping from top reason code to action (e.g. `INCOME_MISMATCH` → "Request source of funds"; `LOCATION_ANOMALY` → "Verify account owner / device"; `BEHAVIOUR_CHANGE` with rising losses → "Safer Gambling check-in"). Each action also names a team (AML / Fraud / Safer Gambling).

**Inputs:** step 2 outputs.

**Outputs:** `data/scores/risk_scores.csv` (`player_id, score, band, team, top_reason_code`) and `data/scores/alerts.json` (full alert objects with the reason list and recommended action).

**Tool / library:** `scikit-learn` (`IsolationForest`), `pandas`. Optional: `lightgbm` or `xgboost` + `shap`.

**Script:** `backend/pipeline/detect.py`

**Owner:** TBD

**Done when:** every alert has at least one reason with evidence values, scores fall in 0–100, bands follow the thresholds in `DESIGN.md`, and no alert has an empty explanation.

---

## Step 4 — Validation

**What to build:** measure detection quality against `scenario_labels.csv`.

**Metrics:**
- recall per anomaly type
- precision@k for k = 25, 50, 100 (how many top-ranked alerts are true injected cases)
- the same precision@k for a rules-only baseline, for comparison
- the false-positive rate on normal players

**Inputs:** `data/scores/risk_scores.csv`, `data/synthetic/scenario_labels.csv`.

**Outputs:** `data/scores/validation_report.json` and a human-readable `docs/VALIDATION.md` (tables + 3 example false positives with an explanation).

**Tool / library:** `scikit-learn.metrics`, `pandas`.

**Script:** `backend/pipeline/validate.py`

**Owner:** TBD

**Done when:** the report runs in one command, every anomaly type has a recall number, the combined score beats rules-only on precision@50, and weights/thresholds chosen here are copied back into `detect.py` and `DESIGN.md`.

---

## Step 5 — API

**What to build:** a FastAPI service that reads the step 3 outputs and serves them to the dashboard.

**Endpoints (draft):**
| Method | Path | Returns |
|---|---|---|
| GET | `/alerts?band=&team=&type=&status=&sort=` | Ranked alert list (summary fields) |
| GET | `/alerts/{alert_id}` | Full alert: reasons, evidence, recommended action |
| GET | `/players/{player_id}` | Profile + recent transactions |
| GET | `/players/{player_id}/peers` | Player vs own baseline vs peer distribution, per feature |
| GET | `/players/{player_id}/network` | Linked players (stretch) |
| POST | `/alerts/{alert_id}/decision` | Record a decision: `accept / escalate / close` + note |
| GET | `/health` | `{"status": "ok"}` |

**Jube:** alerts above a score threshold get pushed to Jube as cases, and decisions sync back. The integration method (Jube HTTP API vs. a manual import) is **TBD**. This is optional for the MVP: decisions can be stored in a local JSON/SQLite file first.

**Inputs:** `data/scores/alerts.json`, `data/features/*.parquet`, `data/synthetic/*.csv`.

**Outputs:** `backend/app/main.py`, `backend/app/schemas.py` (pydantic models). Add any new dependency to the root `requirements.txt`. Interactive docs are served automatically at `/docs`.

**Tool / library:** `fastapi`, `uvicorn`, `pydantic`. CORS enabled for the local frontend.

**Owner:** TBD

**Done when:** `uvicorn backend.app.main:app` starts, every endpoint returns valid JSON when tested with `curl`, and the response shapes are documented in `/docs`.

---

## Step 6 — Dashboard

**What to build:** the investigator UI described in `DESIGN.md`: alert queue, player detail panel, "why flagged" list, peer comparison chart and recommended action with decision buttons.

**Inputs:** the API from step 5 (or `frontend/mock/alerts.json` while the API is in progress).

**Outputs:** `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`.

**Tool / library:** plain HTML/CSS/JS with `fetch()`. Chart: hand-built SVG or Chart.js (**TBD**). Fonts: IBM Plex Sans / Mono.

**Owner:** TBD

**Done when:** an investigator can, using only the keyboard, open the highest-risk alert, see score + reasons + peer chart + recommended action on one screen, and record a decision. Risk is never shown by colour alone, and "SYNTHETIC DATA" is visible.

---

## Step 7 — Bonus features

Only start after steps 1–6 work end to end. Suggested order:

| Bonus | What to build | Tool | Done when |
|---|---|---|---|
| Network analysis | Graph of players sharing devices / payment methods / addresses. Flag clusters and add a `LINKED_PLAYERS` reason | `networkx` | Injected `linked_ring` players appear as a cluster and the reason shows on their alerts |
| Automated recommendations | Expand the step 3 mapping to cover combinations of reasons | Python | Every alert has a recommendation with a one-line rationale |
| Jube integration | Push alerts / sync decisions | Jube API (TBD) | A decision made in the dashboard appears in Jube |
| ML model + SHAP | Train on injected labels and map SHAP top features onto reason items | `lightgbm` / `xgboost`, `shap` | Improves precision@50 in `VALIDATION.md` without breaking explanations |
| LLM summary | 2–3 sentence summary written **only** from the alert JSON | LLM provider **TBD** | The summary never contains a number or fact missing from the evidence (spot-check 10 alerts) |

**Owner:** TBD

---

## Step 8 — Demo

**What to build:** a repeatable demo run.

**Inputs:** everything above, using a fixed seed.

**Outputs:** `docs/DEMO.md` (talk track + click path), slides (location **TBD**), and 3 showcase alerts chosen in advance: one AML (income mismatch), one Fraud (location anomaly), one Safer Gambling (behaviour change).

**Tool / library:** whatever runs the stack locally. A one-command start script (`run_demo.sh` / `run_demo.ps1`) is recommended.

**Owner:** TBD

**Done when:** a teammate who did not build it can start the stack from a clean clone using `README.md` and walk through all 4 requirements within the time limit (**TBD**).
