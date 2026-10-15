# Handoff: Start Here

You're picking up a project whose MVP is built: build steps 1–6 work end to end, plus validation, all five bonus items, the AI layer, compliance indicators and the demo script. This page tells you what to read, what's settled, what's open, and what to do next.

## 0. Build status (2026-10-15)

| Step | Status | Where |
|---|---|---|
| 1 Synthetic data | Done | `backend/pipeline/generate_data.py` |
| 2 Features | Done; also compliance features and per-transaction flags | `backend/pipeline/build_features.py` |
| 2b AI risk model | Done: gradient boosting + SHAP, scored out-of-fold | `backend/pipeline/train_model.py` |
| 3 Detection and scoring | Done | `backend/pipeline/detect.py` |
| 4 Validation | Done; all "done when" checks pass | `backend/pipeline/validate.py`, `docs/VALIDATION.md` |
| 5 API | Done (decisions stored locally, no Jube yet); plus timeline, stats, model card, case report and AI endpoints | `backend/app/` |
| 6 Dashboard | Done; keyboard-only flow tested in Chrome. Bare-bones panels for the AI summary, Ask, queue search, timeline, transaction flags and case report (ready for polish) | `frontend/` |
| 7 Bonus | Network analysis, automated recommendations, ML + SHAP, LLM summary / Q&A / search (free providers) and structuring + 24-hour-rule indicators done; Jube not started | `detect.py`, `train_model.py`, `backend/app/ai.py` |
| 8 Demo | `docs/DEMO.md` and `run_demo.ps1` / `run_demo.sh` done; slides and time limit TBD | `docs/DEMO.md` |

Quick start: `.\run_demo.ps1` (Windows) or `./run_demo.sh`.

## 1. Read in this order (~30 min)

1. [README.md](../README.md): the problem, our solution, anomaly types, stack.
2. [docs/SCOPE.md](SCOPE.md): what the MVP is and what we're **not** building.
3. [PRODUCT.md](../PRODUCT.md): who the users are and how success is judged.
4. [docs/WORKFLOW.md](WORKFLOW.md): the build steps, file names and "done when" checks. **This is your main working document.**
5. [DESIGN.md](../DESIGN.md): read before building the dashboard (step 6).
6. [docs/PROMPTS.md](PROMPTS.md): log any AI prompts you use here.

## 2. Already decided

- Topic: **sports betting only**, all data **synthetic**.
- Stack: Python + FastAPI backend, plain HTML/CSS/JS frontend, Jube for alerts and cases.
- Detection: rules + Isolation Forest + peer-group z-scores + a supervised model (scikit-learn gradient boosting + SHAP, chosen over LightGBM/XGBoost because it needs no extra install). LLM features use free providers only (Ollama, Groq, Gemini), each with a non-LLM fallback.
- Four anomaly types: income mismatch, peer deviation, location anomaly, behaviour change. Also flagged: money movement, linked players, structuring and the $10,000 24-hour reporting threshold.
- One 0–100 risk score with bands Low / Medium / High / Critical, always shown as **number + label**.
- Every alert must have reasons with evidence values. LLM text may only restate computed evidence.
- File names and folder layout: see `WORKFLOW.md` and the README project structure.
- Look and feel: calm, regulatory, high-contrast, not casino-like (see `DESIGN.md`).

## 3. Still TBD

Everything undecided is collected in **one place**: the [Open items](#6-open-items) list at the bottom of this page, including who should decide each item and where it gets decided.

## 4. Your first three tasks

The original first tasks (scaffold, step 1, mock alerts) are done. Next:

1. **Assign owners and confirm decisions**: fill in the team, then review the resolved open items below (especially #4, #5, #7, #8), since they were settled by the build, not by the team.
2. **Rehearse the demo** in `docs/DEMO.md` from a clean clone and set the time limit (#14).
3. **Polish the new AI and investigation panels** (frontend) and **pick a free LLM for the demo** (#11). Remaining stretch: Jube integration (decisions already go through `POST /alerts/{id}/decision`, which is where a Jube sync would hook in) and peer-deviation recall (70%, still the weakest type).

## 5. Definition of done (hackathon demo)

- [x] One command (or a short documented sequence) runs data → features → scoring → API → dashboard from a clean clone (`run_demo.ps1` / `run_demo.sh`).
- [x] The queue shows alerts covering **all four anomaly types**, ranked by risk score.
- [x] Every alert shows score + label, a "why flagged" list with real numbers, a peer comparison and a recommended action.
- [x] An investigator can record a decision (accept / escalate / close with reason, assign to team).
- [x] `docs/VALIDATION.md` reports recall per anomaly type and precision@k vs. a rules-only baseline.
- [x] "SYNTHETIC DATA" is visible in the UI. No real data and no confidential brief text is in the repo.
- [ ] Three showcase alerts (AML, Fraud, Safer Gambling) are rehearsed in `docs/DEMO.md`. *(Chosen and scripted; a human rehearsal is still needed.)*
- [x] At least one bonus item works (all five; plus the AI risk model, AI summaries / Q&A / search and compliance indicators).

## 6. Open items

Every TBD across the docs, in one list. "Team lead" means whoever coordinates the team; until roles are assigned, the whole team decides.

The **Status** column records what the build used. "Built as" items work but were not chosen by the team, so confirm or change them.

| # | Open item | Who should decide | Where it gets decided / recorded | Status |
|---|---|---|---|---|
| 1 | Team members and roles | Team lead | README "Team" | Open |
| 2 | Owner for each build step (1–8) | Team lead | `WORKFLOW.md` owner lines | Open |
| 3 | GitHub repository URL (must be **private**) | Team lead | `git remote`, README | Open: current repo is `github.com/ellitellicity-commits/OLG-AntiMoney-Laundering`; confirm it is private |
| 4 | Python version (3.11 suggested, not confirmed) | Backend / data owner | README "Getting started" | Built as: tested on 3.14 only (the version on the build machine) |
| 5 | Dataset size and injection rates (draft: 5,000 players, 180 days, 3–5% risky) | Data owner (step 1) | `WORKFLOW.md` step 1, `generate_data.py` config | Built as: 5,000 players, 180 days, 223 injected (4.5%, including 30 structuring) plus 450 benign-but-unusual normal players |
| 6 | Peer-group definition (draft: age band × income band × region) | Detection owner (step 2) | `WORKFLOW.md` step 2 | Built as drafted, falling back to age × income, then income, for groups under 30 |
| 7 | Score weights and z-score threshold (draft: \|z\| > 3) | Detection owner (steps 3–4) | `detect.py`, `docs/VALIDATION.md` | Built as: z > 3 (upward only, robust z on a log scale); points in `detect.py` |
| 8 | Risk-band cut-offs (draft: Low 0–39, Medium 40–69, High 70–89, Critical 90–100) | Detection owner, after validation | `DESIGN.md` §2, `detect.py` | Kept as drafted after validation; alerts at 40+ |
| 9 | Jube integration method (HTTP API vs manual import), version and setup (Docker if supported) | Backend owner (step 5) | `WORKFLOW.md` step 5, README "Getting started" | Open; decisions stored in `data/decisions.json` for now |
| 10 | Chart library (hand-built SVG vs Chart.js) | Frontend owner (step 6) | `DESIGN.md` §7.4 | Built as: hand-built SVG (no dependency) |
| 11 | LLM provider, if summaries are used at all | Team lead + bonus owner (step 7) | `WORKFLOW.md` step 7, README "AI features" | Built as: auto-detects free Ollama, Groq or Gemini; built-in fallbacks without one. Pick one for the demo (Ollama suggested: offline) |
| 12 | Deployment target (assumed: local laptop demo) | Team lead | `PRODUCT.md` Stack | Built as: local laptop; the API also serves the dashboard at `/app/` |
| 13 | Dark theme for the dashboard (not needed for MVP) | Frontend owner | `DESIGN.md` §2 | Open (not built) |
| 14 | Demo length, slide location, submission deadline | Team lead (check ThunderHacks rules) | `WORKFLOW.md` step 8, `docs/DEMO.md` | Open |
