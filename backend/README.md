# Backend

Data pipeline (WORKFLOW steps 1–4) and FastAPI service (step 5). Tested with Python 3.13.

## Quick start (from the repo root)

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

python -m backend.pipeline.run_all  # ~1.5 min: data -> features -> scores -> validation
uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000/docs. Endpoint details are in [docs/API.md](../docs/API.md).

Run the tests (they build a small dataset in a temp folder, so they never touch `data/`):

```bash
python -m pytest -q
```

## Layout

```
backend/
├── pipeline/
│   ├── common.py          shared paths, regions, income bands, windows, band cut-offs
│   ├── generate_data.py   step 1: seeded synthetic players / transactions / identifiers / labels
│   ├── build_features.py  step 2: 30-day vs 90-day baseline features, peer-group stats
│   ├── detect.py          step 3: rules + peer z-scores + Isolation Forest -> score, reasons, actions
│   ├── validate.py        step 4: recall, precision@k vs rules-only, docs/VALIDATION.md
│   ├── export_mock.py     writes frontend/mock/alerts.json from real alerts
│   └── run_all.py         runs steps 1-4
└── app/
    ├── main.py            FastAPI app and endpoints
    ├── schemas.py         pydantic response / request models
    ├── store.py           loads pipeline outputs; SQLite decision store
    └── network.py         networkx graph of shared devices / payment methods / addresses
```

## How the score works

1. **Rules** emit reasons per anomaly type (income mismatch, cash cycling, location, behaviour change, linked players).
2. **Peer z-scores**: robust z (median / IQR, log scale for money) within `age_band x income_band x home_region`,
   falling back to broader groups below 30 players. A feature flags at z >= 3 **and** a material amount.
3. **Isolation Forest** over 18 features adds up to 15 points for the top 5% most unusual players.

Each reason carries `points`. Points are summed per anomaly type, each type is capped at 50, and the total is capped at 100.
So every point of the score traces back to a reason with evidence values. Bands: Low 0–39, Medium 40–69, High 70–89, Critical 90–100.
Alerts are players scoring 40 or more.

The team and recommended action come from the anomaly type with the most points. Heavy losses relative to income always add a Safer Gambling secondary action.

## Synthetic data

`generate_data.py` (seed 42, 5,000 players, 180 days ending 2026-09-30) injects 40 players per scenario:

| Scenario | What is injected |
|---|---|
| `income_mismatch` | low-income profile depositing 1–4x monthly income; half also cash-cycle (deposit, bet little, withdraw) |
| `peer_deviation` | stakes 12–25x the player's normal, for the whole period |
| `location_anomaly` | account takeover: new device, foreign IPs, impossible travel, withdrawals to a new payment method |
| `behaviour_change` | last 3–5 weeks: deposits 3–6x, sessions 2–3.5x, late-night play, loss chasing |
| `linked_ring` | 8 rings of 5 sharing devices / payment methods / addresses, betting opposite sides of the same events |

Benign noise is included on purpose, so the false-positive rate is meaningful: travellers on legitimate trips, households sharing an address or tablet, and wealthy high-stakes players.

Tune sizes and rates in `CONFIG` at the top of `generate_data.py`, and thresholds and points in `detect.py`.
