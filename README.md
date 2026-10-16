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
| 1. Detect unusual or suspicious activity | Rules, peer statistics, two unsupervised AI methods (behaviour clustering, Isolation Forest) and a supervised AI model (gradient boosting + SHAP) flag players; every transaction also gets its own flags; a watchlist surfaces unusual players no rule caught |
| 2. Contextual risk assessment | Every flag compares the player with their own 90-day history, with demographic peers **and** with players who bet like them; the declared income is checked against the occupation |
| 3. Investigation prioritization | One 0–100 score that keeps strong cases ordered (no pile-up at 100), a confidence rating with the reasons an alert may be innocent, and one ranked queue across AML, Fraud and Safer Gambling, sortable by risk, recency or AI probability and searchable in plain English |
| 4. Investigator experience | Each alert opens on an Overview tab (AI summary, key facts, confidence, strongest reasons, recommended action), with Evidence, Activity, Network-graph and Ask-AI tabs, a printable case report, an audit trail with investigator names, and an Overview screen of queue-wide risk |

All five bonus items are built: synthetic risky-player data, validation against those scenarios (including populations the AI never saw), automated recommendations, network analysis with a graph, and an integrated overview dashboard. For regulatory compliance, the tool flags FINTRAC-style indicators (structuring, the $10,000 24-hour rule), sanctions-screening matches, unverified identities and PEPs, third-party funding and U-turn withdrawals. [docs/DATA_INTEGRATION.md](docs/DATA_INTEGRATION.md) shows how it would run on real data. See [docs/SCOPE.md](docs/SCOPE.md) for what's in and what's not.

## Anomaly types we detect

| Type | Example | Signal used |
|---|---|---|
| Income mismatch | A player with a declared $40–60k income deposits $18,000 in a month | Deposits ÷ income estimate; rule threshold |
| Peer deviation | Average stake is 12× the median for the same age, income and region group | Peer-group z-score |
| Location anomaly | Bets from Ontario and from another country within an hour | Distinct IP regions, share of activity outside home region, impossible travel |
| Behaviour change | Weekly deposits triple and betting moves to late night over 3 weeks | Current 30 days vs own 90-day baseline; Isolation Forest |
| Structuring (compliance) | Two $9,500 deposits a few hours apart, or five smaller deposits in one day adding up past $10,000 | Rolling 24-hour deposit totals; deposits of $8,000–$9,999.99 |
| Reporting threshold (compliance) | $10,000 or more deposited within 24 hours (FINTRAC-style 24-hour rule) | Rolling 24-hour deposit totals |
| Occupation mismatch | A line cook declaring a $120k+ income, depositing 7× a cook's monthly pay | Declared income band vs typical income for the occupation |
| Money movement (layering) | Money in and out with little betting; near-certain bets; deposits withdrawn within 72 hours | Turnover ÷ deposits, low-odds share, quick cash-outs |
| Third-party funding and U-turns | Deposits from a card in someone else's name, withdrawn to the player's own account | Payment-method holder check; withdrawal method vs the deposit it followed |
| Dormant account reactivated | Silent for five months, then $40,000 moves through in a month | Days inactive before this month |
| Identity and screening | Large deposits on an unverified identity; a sanctions-screening match; a PEP | KYC status, screening result, PEP flag |
| Linked players | Six accounts sharing a device, card and address | Shared-identifier graph |

Each transaction is also flagged on its own: outside Ontario, impossible travel, new device or payment method, a deposit 5× the player's median, just under or part of $10,000 within 24 hours, a low-odds bet, a third-party card, a U-turn withdrawal, or a withdrawal within 72 hours of a deposit.

**How the score works.** Every flag is a reason with points. Within one anomaly type the strongest flag counts in full and the rest at half, so five correlated deposit flags don't outrank independent evidence. Points count one-for-one up to 70, then progressively less, so the score stays between 0 and 99 and strong cases stay ordered instead of all reading 100. Equal scores are ordered by total points, then the AI model's probability. Each alert also gets a **confidence** (High / Medium / Low) from how many independent kinds of evidence agree, the AI model and any **mitigating factors**: reasons the activity may be innocent, shown on the alert.

## AI features (free)

| Feature | What it does | Runs on |
|---|---|---|
| **AI risk model** | Gradient boosting learns which feature combinations match the labelled risk scenarios. Every player is scored by a model that never saw them (5-fold out-of-fold), and SHAP names the features that drove the score. The result is one more reason with points, never a black box; it also orders equal scores and feeds the confidence rating. | scikit-learn + SHAP, locally (no account) |
| **Behaviour groups** | Unsupervised clustering (k-means) groups players by how they bet, so each player is also compared with people who share their betting style, not only their demographics. | scikit-learn, locally |
| **Watchlist (emerging risk)** | The Isolation Forest and the AI model flag players whose pattern is very unusual or risk-like even though no rule reached the alert line; they are listed separately instead of crowding the queue. | scikit-learn, locally |
| **Case summary** | 3–4 sentences at the top of each alert, written only from the computed evidence. Every number is checked against the case file: if the model invents a figure, it is asked to rewrite once, then the built-in template is shown instead. | Free LLM (below), or the built-in template |
| **Ask about this case** | Questions about one alert, answered only from that case's evidence. Any number not found in the evidence is flagged under the answer. | Free LLM (below) |
| **Ask the queue** | Plain English like "recent fraud alerts over 80" becomes queue filters. Invalid values are dropped, never guessed. | Free LLM, or a keyword parser with no model at all |

Measured effect of the AI risk model (synthetic data, [docs/VALIDATION.md](docs/VALIDATION.md)): recall rises from 92% to 96% of injected players, and peer-deviation recall from 48% to 72%, with no meaningful change in false positives (0.38% → 0.40% of normal players). Trained on one population, the whole system still catches 96–97% of risky players in two populations it never saw.

**Turning on a free LLM.** Pick one. The API finds it automatically (`GET /ai/status` shows what it found):

| Option | Setup | Notes |
|---|---|---|
| **Ollama** (recommended for the demo) | Install from ollama.com, then `ollama pull llama3.2` | Local and offline; data never leaves the laptop. The first answer can take a few seconds. |
| **Groq** free tier | Create a key at console.groq.com and put `GROQ_API_KEY=...` in a `.env` file in the repo root | Very fast; needs internet. Default model `openai/gpt-oss-20b`. |
| **Gemini** free tier | Create a key at aistudio.google.com and put `GEMINI_API_KEY=...` in `.env` | Needs internet. Default model `gemini-flash-latest`. Google may use free-tier inputs to improve its products; fine here because all data is synthetic. |

Optional settings in `.env`: `LLM_PROVIDER=ollama|groq|gemini|none` (default `auto`) and `LLM_MODEL=...` to override the model (free model names change; check the provider's model list if a default stops working). `.env` is git-ignored. Restart the API after editing it.

## Tech stack

| Layer | Tool | Purpose |
|---|---|---|
| Synthetic data | Python, numpy, pandas, Faker | Generate players and transactions with labelled risky behaviour |
| Features | pandas, pyarrow | Per-player, baseline, peer-group and compliance features; per-transaction flags |
| Detection | Rules, z-scores, scikit-learn (Isolation Forest, k-means behaviour groups) | Find anomalies and produce reasons |
| AI risk model | scikit-learn `HistGradientBoostingClassifier` + SHAP | Supervised model whose explanations become a reason with points |
| Network | networkx | Find linked players sharing devices, payment methods or addresses |
| AI summaries, Q&A, search | Free LLM: Ollama, Groq or Gemini (standard-library client, no SDK) | Plain-language text limited to computed evidence, with a number check |
| API | FastAPI, uvicorn, pydantic | Serve alerts, watchlist, player detail, peers, timeline, overview statistics, AI features, case reports and the audit trail; record decisions |
| Alerting and cases | Jube | Case management for alerts (integration method TBD) |
| Frontend | Plain HTML, CSS, JavaScript | The investigator dashboard |

## Project structure

```
.
├── README.md
├── requirements.txt        # Python dependencies (repo root)
├── .gitignore
├── PRODUCT.md              # who it's for, goals, success criteria
├── DESIGN.md               # visual direction for the dashboard (implemented)
├── run_demo.ps1 / run_demo.sh  # one-command demo: venv, pipeline, API, dashboard
├── docs/
│   ├── HANDOFF.md          # start here
│   ├── SCOPE.md
│   ├── WORKFLOW.md
│   ├── PROMPTS.md
│   ├── VALIDATION.md       # generated by validate.py (step 4)
│   └── DEMO.md             # talk track and click path (step 8)
├── backend/
│   ├── pipeline/           # common.py, generate_data.py, build_features.py, train_model.py, detect.py,
│   │                       # cross_seed.py, validate.py, check_data.py
│   └── app/                # FastAPI: main.py, schemas.py, ai.py (free LLM layer), report.py (case report)
├── data/
│   ├── synthetic/          # players.csv, transactions.csv, linked_identifiers.csv, scenario_labels.csv,
│   │                       # benign_labels.csv, metadata.json
│   ├── features/           # player_features, peer_stats, transaction_flags, ml_scores (.parquet)
│   ├── models/             # risk_model.joblib, model_card.json (AI risk model)
│   ├── scores/             # risk_scores.csv, alerts.json, watchlist.json, cross_seed.json, validation_report.json
│   ├── decisions.json      # investigator decisions recorded through the API
│   └── ai_cache.json       # cached AI case summaries
└── frontend/               # index.html, styles.css, app.js
    └── mock/               # alerts.json: hand-written sample data for building the UI before the API exists
```

Everything in `data/` (`.csv`, `.parquet`, `.json`) is generated and git-ignored. Recreate it by running the pipeline.

## Documentation index

| Doc | What it's for |
|---|---|
| [docs/HANDOFF.md](docs/HANDOFF.md) | Start here: reading order, decisions made, open items, first tasks |
| [PRODUCT.md](PRODUCT.md) | Users, jobs to be done, goals, tone, anti-goals, success criteria |
| [docs/SCOPE.md](docs/SCOPE.md) | MVP vs stretch, how each requirement is demonstrated, what we're not building |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Build order with inputs, outputs, tools, owners and "done when" for each step |
| [DESIGN.md](DESIGN.md) | Design direction: colours, type, spacing, risk badges, components |
| [docs/DESIGN_SENTINEL.md](docs/DESIGN_SENTINEL.md) | Alternative "Sentinel" design from the static mock (`frontend/mock_frontend.html`); not yet adopted |
| [docs/JUBE.md](docs/JUBE.md) | Jube case-management integration: mock demo and real-Jube setup |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Field proposal behind the static mock, with a mapping to the implemented API |
| [docs/PROMPTS.md](docs/PROMPTS.md) | Log of AI prompts used, per build step |
| [docs/VALIDATION.md](docs/VALIDATION.md) | Measured recall, precision@k and false positives (generated) |
| [docs/DEMO.md](docs/DEMO.md) | Demo talk track, click path and showcase alerts |
| [docs/DATA_INTEGRATION.md](docs/DATA_INTEGRATION.md) | Data contract, where each field would come from, other gaming environments, running on real data |

## Getting started

**Quick start (one command)** from the repo root:

```powershell
.\run_demo.ps1                 # Windows PowerShell
./run_demo.sh                  # macOS / Linux / Git Bash
```

This creates `.venv`, installs dependencies, runs the pipeline (about 3 minutes, including the cross-seed test), starts the API and opens the
dashboard at http://127.0.0.1:8000/app/. Add `-SkipPipeline` (`--skip-pipeline`) to reuse existing data.
If PowerShell blocks the script: `powershell -ExecutionPolicy Bypass -File .\run_demo.ps1`.

**Step by step**

**1. Prerequisites**
- Python: tested with **3.14** (the only version on the build machine; 3.11 was suggested but is unconfirmed, see open item 4 in [docs/HANDOFF.md](docs/HANDOFF.md))
- Git
- Jube: not integrated yet (stretch). Decisions are stored in `data/decisions.json` instead.

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

**4. Run the data pipeline**

```bash
python backend/pipeline/generate_data.py   # step 1: synthetic data (seeded, ~30 s)
python backend/pipeline/build_features.py  # step 2: features, peer stats, transaction flags (~10 s)
python backend/pipeline/train_model.py     # step 2b: AI risk model + SHAP, out-of-fold (~10 s)
python backend/pipeline/detect.py          # step 3: reasons, scores, confidence, alerts, watchlist (~10 s)
python backend/pipeline/cross_seed.py      # step 3b: test on two populations the AI never saw (~2 min)
python backend/pipeline/validate.py        # step 4: metrics + docs/VALIDATION.md
```

**5. Start the API**

```bash
uvicorn backend.app.main:app --reload
```

The API runs at http://127.0.0.1:8000, with interactive docs at http://127.0.0.1:8000/docs.

**6. Open the dashboard**

The API also serves the dashboard at http://127.0.0.1:8000/app/. You can instead open `frontend/index.html`
directly or serve the folder (`python -m http.server 5500 --directory frontend`); it then calls the API at
`http://127.0.0.1:8000` (override with `?api=http://host:port`). If the API is not running, the dashboard falls
back to five hand-written alerts in `frontend/mock/alerts.json` and says so in a banner.

**Keyboard:** `↑`/`↓` move through the queue, `Enter` opens an alert, `D` jumps to the decision buttons,
`Esc` returns to the queue, `/` focuses search.

## Results (synthetic data, seed 42)

From [docs/VALIDATION.md](docs/VALIDATION.md): 296 alerts from 5,000 players. Of the 289 planted risky players
(9 scenarios), 96% are alerted (100% for seven scenarios, income mismatch 98%, peer deviation 72%), and the
watchlist catches 6 more that no rule reached. The top 100 alerts are all real cases. Only 0.40% of normal
players are alerted; legacy fixed-threshold rules raise 394 alerts and flag 2.76%.

- **Prioritisation:** 46 distinct scores, highest 97; no score holds more than 30 alerts (11 once total points
  break ties), instead of 165 alerts tied at 100.
- **Confidence:** High- and Medium-confidence alerts are all real cases; every false positive sits in Low.
- **AI model:** recall 92% → 96% with it (peer deviation 48% → 72%), false positives essentially unchanged.
- **Never-seen populations:** 96% and 97% caught, 0.55–0.66% of normal players alerted, AI ROC-AUC 0.998–0.999.

These numbers come from data the same team generated, so they show the pipeline works end to end, not
real-world accuracy.

## Team

| Name | Role |
|---|---|
| TBD | TBD |

Team members and roles have not been provided yet. Once they are, add them here and fill in the owner lines in [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Confidentiality

**The OLG challenge brief is confidential and must not be copied into this repository, in full or in part (including the PDF).** Our docs describe the challenge in our own words only.

The OLG challenge brief is **confidential and for registered ThunderHacks 2026 participants only**. Do not commit it, quote it at length, or share it outside the team. All data in this repository is synthetic. No real OLG player or transaction data is used.
