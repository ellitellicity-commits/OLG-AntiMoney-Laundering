# OLG Anti-Money Laundering

**A sports-betting risk-review tool that finds unusual player behaviour, compares it with the player's own history and with similar players, ranks it, and explains every flag in plain language.**

Built for ThunderHacks 2026, OLG sponsor challenge: *Intelligent Player Protection & Fraud Detection*. Our scope is sports betting only, using synthetic data.

## The Problem

OLG (Ontario Lottery and Gaming Corporation) has investigators in three teams. **Anti-Money Laundering** looks for criminal money moving through betting accounts. **Fraud** looks for stolen or misused accounts. **Safer Gambling** looks for players who may be harming themselves. Every day these teams review a very large number of transactions and alerts.

Most of those alerts come from fixed rules, such as "deposit over $X". Rules fire often, but they don't say *why* something looks suspicious, whether it is unusual *for this person*, or whether it deserves an investigator's time. A $5,000 deposit means something very different for a high earner with a long, steady history than for a student who usually deposits $50. Investigators end up spending their time sorting through noise instead of investigating.

## Our Solution

The tool scores each player from 0 to 100, ranks them in one queue, and shows the evidence behind every score. It maps to the challenge's four requirements:

| Requirement | What the tool does |
|---|---|
| 1. Detect unusual or suspicious activity | Rules, Isolation Forest and peer-group z-scores flag four anomaly types (below) |
| 2. Contextual risk assessment | Every flag compares the player with their own 90-day baseline **and** with a peer group of similar players |
| 3. Investigation prioritization | One 0–100 risk score with Low (0–39) / Medium (40–69) / High (70–100) bands, in a single ranked queue across AML, Fraud and Safer Gambling |
| 4. Investigator experience | A dashboard showing the score, a "why flagged" list with the actual numbers, a peer comparison chart and a recommended next action |

Bonus items we're targeting: synthetic risky-player data, validation of detection rules, automated recommendations, network analysis of linked players, and a unified risk dashboard. See [docs/SCOPE.md](docs/SCOPE.md) for what's in the MVP and what's stretch.

## Anomaly types we detect

| Type | Example | Signal used |
|---|---|---|
| Income mismatch | A player with a declared $40–60k income deposits $18,000 in a month | Deposits ÷ income estimate; rule threshold |
| Peer deviation | Average stake is 12× the median for the same age, income and region group | Peer-group z-score |
| Location anomaly | Bets from Ontario and from another country within an hour | Distinct IP regions, share of activity outside home region, impossible travel |
| Behaviour change | Weekly deposits triple and betting moves to late night over 3 weeks | Current 30 days vs own 90-day baseline; Isolation Forest |

## Tech stack

| Layer | Tool | Purpose |
|---|---|---|
| Synthetic data | Python, numpy, pandas, Faker | Generate players and transactions with labelled risky behaviour |
| Features | pandas, pyarrow | Per-player, baseline and peer-group features |
| Detection | scikit-learn (Isolation Forest), rules, z-scores | Find anomalies and produce reasons |
| Optional ML | LightGBM or XGBoost + SHAP | A stronger model whose explanations map onto the same reasons |
| Network (stretch) | networkx | Find linked players sharing devices, payment methods or addresses |
| Optional summaries | LLM (provider TBD) | Plain-language summaries limited to computed evidence |
| API | FastAPI, uvicorn, pydantic | Serve alerts, player detail and peer data; record decisions |
| Alerting and cases | Jube | Case management for alerts (integration method TBD) |
| Frontend | Plain HTML, CSS, JavaScript | The investigator dashboard |

## Project structure (planned)

```
.
├── README.md
├── requirements.txt        # Python dependencies (repo root)
├── .gitignore
├── PRODUCT.md              # who it's for, goals, success criteria
├── DESIGN.md               # draft visual direction for the dashboard
├── docs/
│   ├── HANDOFF.md          # start here
│   ├── SCOPE.md
│   ├── WORKFLOW.md
│   ├── PROMPTS.md
│   ├── API_CONTRACT.md     # fields + endpoints the dashboard needs
│   ├── VALIDATION.md       # produced in build step 4
│   └── DEMO.md             # produced in build step 8
├── backend/
│   ├── pipeline/           # generate_data.py, build_features.py, detect.py, validate.py
│   └── app/                # FastAPI: main.py, schemas.py
├── data/
│   ├── synthetic/          # players.csv, transactions.csv, linked_identifiers.csv, scenario_labels.csv
│   ├── features/           # player_features.parquet, peer_stats.parquet
│   └── scores/             # risk_scores.csv, alerts.json, validation_report.json
└── frontend/
    ├── mock_frontend.html  # static design mock: 8 fictional players, opens by double-click (exists now)
    └── index.html          # live dashboard calling the API (built later in step 6, with styles.css and app.js)
```

Generated files in `data/` (`.csv`, `.parquet`) are git-ignored. Recreate them by running the pipeline.

## Documentation index

| Doc | What it's for |
|---|---|
| [docs/HANDOFF.md](docs/HANDOFF.md) | Start here: reading order, decisions made, open items, first tasks |
| [PRODUCT.md](PRODUCT.md) | Users, jobs to be done, goals, tone, anti-goals, success criteria |
| [docs/SCOPE.md](docs/SCOPE.md) | MVP vs stretch, how each requirement is demonstrated, what we're not building |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Build order with inputs, outputs, tools, owners and "done when" for each step |
| [DESIGN.md](DESIGN.md) | Draft design direction: colours, type, spacing, risk badges, components |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Every field the dashboard mock shows, and the 3 endpoints the backend must provide |
| [docs/PROMPTS.md](docs/PROMPTS.md) | Log of AI prompts used, per build step |

## Getting started

> No application code exists yet. Steps 4–6 below only work once build steps 1–6 in [docs/WORKFLOW.md](docs/WORKFLOW.md) are done.

**1. Prerequisites**
- Python: version **TBD** (3.11 suggested; the team still has to confirm it)
- Git
- Jube: setup **TBD**. Check Jube's official documentation for install steps and use its Docker setup if one is supported. Jube is optional for the MVP (see [docs/SCOPE.md](docs/SCOPE.md)).

**2. Create and activate a virtual environment** (from the repo root)

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the data pipeline** (scripts are created in build steps 1–4)

```bash
python backend/pipeline/generate_data.py
python backend/pipeline/build_features.py
python backend/pipeline/detect.py
python backend/pipeline/validate.py
```

**5. Start the API**

```bash
uvicorn backend.app.main:app --reload
```

The API runs at http://127.0.0.1:8000, with interactive docs at http://127.0.0.1:8000/docs.

**6. Open the dashboard**

**Today:** double-click `frontend/mock_frontend.html`. It is a self-contained static mock that needs no server and no API. It shows the target design and the data the backend must supply (see [docs/API_CONTRACT.md](docs/API_CONTRACT.md)).

**Later (after build step 6):** open the live dashboard `frontend/index.html`, a separate file that calls the API. If the browser blocks requests from a `file://` page, serve the folder instead:

```bash
python -m http.server 5500 --directory frontend
```

Then go to http://127.0.0.1:5500.

## Team

| Name | Role |
|---|---|
| TBD | TBD |

Team members and roles have not been provided yet. Once they are, add them here and fill in the owner lines in [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Confidentiality

**The OLG challenge brief is confidential and must not be copied into this repository, in full or in part (including the PDF).** Our docs describe the challenge in our own words only.

The OLG challenge brief is **confidential and for registered ThunderHacks 2026 participants only**. Do not commit it, quote it at length, or share it outside the team. All data in this repository is synthetic. No real OLG player or transaction data is used.
