# Handoff: Start Here

You're picking up a project whose MVP is built: build steps 1–6 work end to end, plus validation, all five bonus items, the AI layer, compliance indicators and the demo script. This page tells you what to read, what's settled, what's open, and what to do next.

## 0. Build status (2026-10-15)

| Step | Status | Where |
|---|---|---|
| 1 Synthetic data | Done; 9 risky scenarios incl. third-party funding, dormant accounts, identity risk; payment methods and KYC / PEP / sanctions fields | `backend/pipeline/generate_data.py` |
| 2 Features | Done; compliance, money-flow (U-turn, quick cash-out, low-odds, third-party), dormancy, occupation and behaviour-group (k-means) features; per-transaction flags | `backend/pipeline/build_features.py` |
| 2b AI risk model | Done: gradient boosting + SHAP, scored out-of-fold | `backend/pipeline/train_model.py` |
| 3 Detection and scoring | Done; overlap-aware soft-capped score, confidence + mitigating factors, watchlist | `backend/pipeline/detect.py` |
| 3b Cross-seed test | Done: the system tested on two populations the AI never saw | `backend/pipeline/cross_seed.py` |
| 4 Validation | Done; all "done when" checks pass | `backend/pipeline/validate.py`, `docs/VALIDATION.md` |
| 5 API | Done (decisions stored locally with investigator names, no Jube yet); plus watchlist, timeline, stats with trends, model card, case report, audit trail and AI endpoints | `backend/app/` |
| 6 Dashboard | Done; tabbed detail (Overview, Evidence, Activity, Network graph, Ask AI), Overview screen, confidence, watchlist, investigator name. Tested in Chrome; ready for visual polish | `frontend/` |
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
- Detection: rules + peer-group z-scores + behaviour groups (k-means) + Isolation Forest + a supervised model (scikit-learn gradient boosting + SHAP, chosen over LightGBM/XGBoost because it needs no extra install). LLM features use free providers only (Ollama, Groq, Gemini), each with a non-LLM fallback.
- Four anomaly types: income mismatch, peer deviation, location anomaly, behaviour change. Also flagged: occupation mismatch, money movement (layering, low-odds betting, quick cash-outs), third-party funding, U-turn withdrawals, dormant accounts, identity & screening (KYC, sanctions, PEP), linked players, structuring and the $10,000 24-hour reporting threshold.
- One 0–99 risk score with bands Low / Medium / High / Critical, always shown as **number + label**. Overlapping flags of one type count half; above 70 points the score rises progressively more slowly (soft cap), so strong cases stay ordered. Every alert has a confidence and its mitigating factors.
- Every decision needs an investigator name (audit trail).
- Every alert must have reasons with evidence values. LLM text may only restate computed evidence.
- File names and folder layout: see `WORKFLOW.md` and the README project structure.
- Look and feel: calm, regulatory, high-contrast, not casino-like (see `DESIGN.md`).

## 3. Still TBD

Everything undecided is collected in **one place**: the [Open items](#6-open-items) list at the bottom of this page, including who should decide each item and where it gets decided.

## 4. Who picks up what (from 2026-10-15)

The functional build is complete against the challenge brief (all four requirements, all five bonus items and
every "winning solution" point; see the README). What remains is polish, robustness and the presentation.
Work on your own git branch and merge into `main`; the two lists below touch different folders, so they
shouldn't collide.

**Frontend owner** (`frontend/` only):
1. Visual polish of the queue, the tabbed detail panel (Overview / Evidence / Activity / Network / Ask AI) and
   the Overview screen. The structure and every data hook exist; keep the rules in `DESIGN.md` (number + label
   for risk, no colour-only meaning, no vanity KPI tiles, "SYNTHETIC DATA" visible).
2. Charts: hover details on the weekly timeline, a nicer network graph (`networkGraph()` in `app.js`).
3. Update `frontend/mock/alerts.json` so the offline fallback shows the new fields (confidence, mitigating
   factors, behaviour group, `points_total`). The code already tolerates them being absent.
4. Accessibility pass on the new tabs, overview and investigator box (keyboard and screen reader).
5. Screenshots for the slides.

**Backend owner** (`backend/` only):
1. Automated tests (pytest): pipeline determinism, every API endpoint, the 422 cases (close without reason,
   assign without team, decision without investigator name), the AI number check (`ai.unverified_numbers`).
2. Confirm it runs on Python 3.11 / 3.12 (3.13 and 3.14 are tested; see open item #4).
3. AI quality: try a larger free model (e.g. `ollama pull qwen2.5:7b`, then `LLM_MODEL=qwen2.5:7b` in `.env`) and
   compare the showcase summaries; `llama3.2` (3B) occasionally misreads meaning even when every number is right.
4. Optional: SQLite for decisions instead of `data/decisions.json`; better peer-deviation recall (72%, the
   weakest type); Jube integration through `POST /alerts/{id}/decision`.

**Whole team / team lead:**
1. Fill in team names and roles (README "Team", open items #1 and #2).
2. Slides: problem → solution → live demo → results (numbers in `docs/VALIDATION.md`).
3. Rehearse `docs/DEMO.md` at least twice after the polish is merged (screens may move) and set the time
   limit (open item #14). Check the ThunderHacks submission rules and deadline.

**Rules that keep the demo and the numbers valid:**
- Run the full pipeline (`.\run_demo.ps1`, about 3 minutes) and check every line under "Checks" in
  `docs/VALIDATION.md` still says **yes** before merging any backend change.
- Don't change `THRESHOLDS`, points or the generator config without rerunning validation: the showcase alert IDs
  and every number in `docs/DEMO.md` and the README depend on them. If they change, update both docs.
- The pipeline must stay deterministic (same seed → identical files); avoid iterating over Python sets when
  writing outputs.
- Never commit the challenge PDF, real data or `.env` (all git-ignored).

**For AI coding agents picking this up:** read this file, then `README.md`, `docs/WORKFLOW.md` and `DESIGN.md`;
run `.\run_demo.ps1` once; log your prompts in `docs/PROMPTS.md` as the earlier sessions did (entries 1.1, 7.1,
7.2 describe how the current build was made and what went wrong along the way).

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
| 4 | Python version (3.11 suggested, not confirmed) | Backend / data owner | README "Getting started" | Built as: tested on 3.14 and 3.13.15 (Windows 11, fresh clone, merge-all-branches) |
| 5 | Dataset size and injection rates (draft: 5,000 players, 180 days, 3–5% risky) | Data owner (step 1) | `WORKFLOW.md` step 1, `generate_data.py` config | Built as: 5,000 players, 180 days, 289 injected (5.8%, 9 scenarios) plus benign-but-unusual normal players (incl. PEPs, unverified identities and false screening matches) |
| 6 | Peer-group definition (draft: age band × income band × region) | Detection owner (step 2) | `WORKFLOW.md` step 2 | Built as drafted, falling back to age × income, then income, for groups under 30 |
| 7 | Score weights and z-score threshold (draft: \|z\| > 3) | Detection owner (steps 3–4) | `detect.py`, `docs/VALIDATION.md` | Built as: z > 3 (upward only, robust z on a log scale); points in `detect.py` |
| 8 | Risk-band cut-offs (draft: Low 0–39, Medium 40–69, High 70–89, Critical 90–100) | Detection owner, after validation | `DESIGN.md` §2, `detect.py` | Kept as drafted after validation; alerts at 40+ |
| 9 | Jube integration method (HTTP API vs manual import), version and setup (Docker if supported) | Backend owner (step 5) | `WORKFLOW.md` step 5, README "Getting started" | Built as: Jube HTTP API (invoke endpoint pushes alerts 70+ as cases keyed on `PlayerId`; case status is pulled back as decisions). Tested against a mock Jube, not a live instance; setup in `docs/JUBE.md` |
| 10 | Chart library (hand-built SVG vs Chart.js) | Frontend owner (step 6) | `DESIGN.md` §7.4 | Built as: hand-built SVG (no dependency) |
| 11 | LLM provider, if summaries are used at all | Team lead + bonus owner (step 7) | `WORKFLOW.md` step 7, README "AI features" | Built as: auto-detects free Ollama, Groq or Gemini; built-in fallbacks without one. Ollama + llama3.2 installed and tested on the build machine; a larger model (e.g. qwen2.5:7b) is worth trying |
| 12 | Deployment target (assumed: local laptop demo) | Team lead | `PRODUCT.md` Stack | Built as: local laptop; the API also serves the dashboard at `/app/` |
| 13 | Dark theme for the dashboard (not needed for MVP) | Frontend owner | `DESIGN.md` §2 | Open (not built) |
| 14 | Demo length, slide location, submission deadline | Team lead (check ThunderHacks rules) | `WORKFLOW.md` step 8, `docs/DEMO.md` | Open |
| 15 | `age` vs `age_band` in `players.csv`, and a `province` field (raised by the static mock) | Data owner (step 1) | `docs/API_CONTRACT.md`, `WORKFLOW.md` step 1 | Built as: `age_band`; every home region is in Ontario |
| 16 | Which design to keep: implemented `DESIGN.md` or the static mock's "Sentinel" (`docs/DESIGN_SENTINEL.md`, `frontend/mock_frontend.html`); also 4 vs 3 risk bands | Frontend owners together | `DESIGN.md` | Open: the live dashboard uses `DESIGN.md` and 4 bands |
