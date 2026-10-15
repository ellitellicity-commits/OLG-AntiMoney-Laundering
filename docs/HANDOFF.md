# Handoff: Start Here

You're picking up a planned-but-unbuilt project. No code exists yet; only these documents do. This page tells you what to read, what's settled, what's open, and what to do first.

## 1. Read in this order (~30 min)

1. [README.md](../README.md): the problem, our solution, anomaly types, stack.
2. [docs/SCOPE.md](SCOPE.md): what the MVP is and what we're **not** building.
3. [PRODUCT.md](../PRODUCT.md): who the users are and how success is judged.
4. [docs/WORKFLOW.md](WORKFLOW.md): the build steps, file names and "done when" checks. **This is your main working document.**
5. [DESIGN.md](../DESIGN.md) and `frontend/mock_frontend.html`: read and open before building the dashboard (step 6).
6. [docs/API_CONTRACT.md](API_CONTRACT.md): the fields and endpoints the backend must provide for the dashboard.
7. [docs/PROMPTS.md](PROMPTS.md): log any AI prompts you use here.

## 2. Already decided

- Topic: **sports betting only**, all data **synthetic**.
- Stack: Python + FastAPI backend, plain HTML/CSS/JS frontend, Jube for alerts and cases.
- Detection: rules + Isolation Forest + peer-group z-scores. LightGBM/XGBoost + SHAP and LLM summaries are optional.
- Four anomaly types: income mismatch, peer deviation, location anomaly, behaviour change.
- One 0–100 risk score with three bands, Low (0–39) / Medium (40–69) / High (70–100), always shown as **number + label + 4-bar meter**.
- Dashboard look and data: `frontend/mock_frontend.html` (static mock) and [API_CONTRACT.md](API_CONTRACT.md) (fields and endpoints). The live frontend will be a separate `frontend/index.html`.
- Every alert must have reasons with evidence values. LLM text may only restate computed evidence.
- File names and folder layout: see `WORKFLOW.md` and the README project structure.
- Look and feel: calm, regulatory, high-contrast, not casino-like (see `DESIGN.md`).

## 3. Still TBD

Everything undecided is collected in **one place**: the [Open items](#6-open-items) list at the bottom of this page, including who should decide each item and where it gets decided.

## 4. Your first three tasks

1. **Scaffold the repo**: create the folders from the README project structure. The root `requirements.txt` and `.gitignore` already exist, and generated `data/` files are ignored. Set up the venv as described in README "Getting started".
2. **Build step 1 (synthetic data)**: write `backend/pipeline/generate_data.py` to the column spec in `WORKFLOW.md`, including `scenario_labels.csv`. Everything else depends on it.
3. **Read `frontend/mock_frontend.html` and [API_CONTRACT.md](API_CONTRACT.md) together.** The mock already contains 8 hand-written alerts in the exact shape the API must return, so the backend and the live frontend can be built in parallel against that contract.

## 5. Definition of done (hackathon demo)

- [ ] One command (or a short documented sequence) runs data → features → scoring → API → dashboard from a clean clone.
- [ ] The queue shows alerts covering **all four anomaly types**, ranked by risk score.
- [ ] Every alert shows score + label, a "why flagged" list with real numbers, a peer comparison and a recommended action.
- [ ] An investigator can record a decision (accept / escalate / close with reason).
- [ ] `docs/VALIDATION.md` reports recall per anomaly type and precision@k vs. a rules-only baseline.
- [ ] "SYNTHETIC DATA" is visible in the UI. No real data and no confidential brief text is in the repo.
- [ ] Three showcase alerts (AML, Fraud, Safer Gambling) are rehearsed in `docs/DEMO.md`.
- [ ] At least one bonus item works (network analysis or Jube integration recommended).

## 6. Open items

Every TBD across the docs, in one list. "Team lead" means whoever coordinates the team; until roles are assigned, the whole team decides.

| # | Open item | Who should decide | Where it gets decided / recorded |
|---|---|---|---|
| 1 | Team members and roles | Team lead | README "Team" |
| 2 | Owner for each build step (1–8) | Team lead | `WORKFLOW.md` owner lines |
| 3 | GitHub repository URL (must be **private**) | Team lead | `git remote`, README |
| 4 | Python version (3.11 suggested, not confirmed) | Backend / data owner | README "Getting started" |
| 5 | Dataset size and injection rates (draft: 5,000 players, 180 days, 3–5% risky) | Data owner (step 1) | `WORKFLOW.md` step 1, `generate_data.py` config |
| 6 | Peer-group definition (draft: age band × income band × region) | Detection owner (step 2) | `WORKFLOW.md` step 2 |
| 7 | Score weights and z-score threshold (draft: \|z\| > 3) | Detection owner (steps 3–4) | `detect.py`, `docs/VALIDATION.md` |
| 8 | Risk-band cut-offs (draft, 3 bands: Low 0–39, Medium 40–69, High 70–100) | Detection owner, after validation | `DESIGN.md` §2, `detect.py` |
| 9 | Jube integration method (HTTP API vs manual import), version and setup (Docker if supported) | Backend owner (step 5) | `WORKFLOW.md` step 5, README "Getting started" |
| 10 | Chart library (hand-built SVG vs Chart.js) | Frontend owner (step 6) | `DESIGN.md` §7.4 |
| 11 | LLM provider, if summaries are used at all | Team lead + bonus owner (step 7) | `WORKFLOW.md` step 7 |
| 12 | Deployment target (assumed: local laptop demo) | Team lead | `PRODUCT.md` Stack |
| 13 | Dark theme for the dashboard (not needed for MVP) | Frontend owner | `DESIGN.md` §2 |
| 14 | Demo length, slide location, submission deadline | Team lead (check ThunderHacks rules) | `WORKFLOW.md` step 8, `docs/DEMO.md` |
| 15 | `age` vs `age_band` in `players.csv` (the mock shows exact age) and adding `province` | Data owner (step 1) | `API_CONTRACT.md`, `WORKFLOW.md` step 1 |
| 16 | When the "Monitoring" indicator turns `stale` (age of last scan) | Backend owner (step 5) | `API_CONTRACT.md` Summary |
