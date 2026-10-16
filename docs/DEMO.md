# Demo

A repeatable walkthrough of all four challenge requirements, the compliance angle and the AI features.
Everything shown is **synthetic** (seed 42).

## Before the demo

1. From a clean clone, run `.\run_demo.ps1` (Windows) or `./run_demo.sh` (macOS / Linux / Git Bash).
   This creates `.venv`, installs `requirements.txt`, runs the pipeline (about 3 minutes, including the
   cross-seed test), starts the API and opens the dashboard at http://127.0.0.1:8000/app/.
2. If you already ran the pipeline, `.\run_demo.ps1 -SkipPipeline` starts in a few seconds.
3. **Turn on the free AI assistant** (README, "AI features"). Ollama is the safest choice because it runs
   offline: install it, run `ollama pull llama3.2` once, and keep it running. The top bar shows
   "AI assistant on · llama3.2 (local)" when it is found. Without it, every AI panel uses its built-in fallback.
4. Open each showcase alert's Overview tab once before presenting: a local model needs a few seconds for the
   first summary, then it is cached in `data/ai_cache.json`.
5. Type your name in the **Investigator** box (top right); decisions are refused without it.
6. Reset recorded decisions before each rehearsal: stop the server, delete `data/decisions.json`, restart.
7. Use a browser window at least 1280 px wide. Keep `docs/VALIDATION.md` open in a second tab.

The showcase alert IDs below are stable for seed 42. If the generator config changes, pick new ones from
`data/scores/alerts.json`.

Time limit: **TBD** (check the ThunderHacks rules). The full talk track runs about 8 minutes; for a 5-minute
slot, keep steps 1–5 and 10, and drop the rest.

## Talk track and click path

### 1. The problem (30 s)

> Investigators get thousands of rule alerts a day with no reasons and no context. A $5,000 deposit means
> one thing for a steady high earner and another for a student who usually deposits $50.

Point at the header: **SYNTHETIC DATA**, 5,000 players, 180 days of sports betting.

### 2. Prioritisation: the queue (45 s) — *Requirement 3*

- One ranked list across AML, Fraud and Safer Gambling. Each badge shows **number + label + meter**, and
  under it a **confidence**.
- The score doesn't pile up at 100: overlapping flags count half, and above 70 points each extra point counts
  less, so strong cases stay ordered. Equal scores are ordered by total evidence, then the AI model.
- **Sort by → Most recent first**, then back to **Highest risk first**.
- Type into **Ask the queue**: `critical AML alerts with linked players` → **Find**. Click **Clear**.

### 3. AML showcase: `ALR-03415`, occupation mismatch (75 s) — *Requirements 1, 2, 4*

Press `/`, type `03415`, press `↓` then `Enter`. The **Overview** tab opens.

- A **line cook declaring $120k+**. The deposits ($27,480 in 30 days) look fine against the declared income,
  so a plain income check misses this player. The occupation check doesn't: a line cook typically earns up to
  $45,000, so the deposits are **7.3× a month's pay**.
- **Case summary** at the top, written by the AI from the evidence below and number-checked.
- **Key facts** strip, then **"Does this truly warrant investigation?"**: High confidence, with the one
  mitigating factor the system found (deposits are in line with the player's own history) shown honestly.
- **Strongest reasons**: occupation mismatch, deposits 52.8× the peer median, money in and out with only 30% bet.
- Click **See all reasons** → **Evidence** tab: every reason with its points (overlapping ones marked "half"),
  the peer chart, and "Players who usually bet like them" (machine-learning behaviour groups).
- Recommended action: **Request proof of income**. Press `D`, `Enter` to accept.

### 4. Compliance: structuring, `ALR-00405` (60 s) — *Winning criterion 7*

Search `00405`.

- **Deposits kept just under the $10,000 reporting threshold** (3 deposits of $8,000–$9,999.99, and 3 times
  deposits each under $10,000 added up past it within 24 hours), plus **$10,000+ within 24 hours**.
- **Activity** tab → **Show flagged only**: each transaction carries its own flags ("Just under $10,000",
  "$10,000+ within 24 hours", "Low-odds bet", "Withdrawn within 72 h of deposit"). The weekly chart shows
  deposits jumping in the last 30 days.
- Click **Case report**: a printable page with the summary, confidence, evidence, compliance profile, flagged
  transactions and the decision history with investigator names. (Indicators for review, not a filing.)

### 5. Money mules: third-party funding, `ALR-02426` (45 s)

Search `02426`.

- A **student** depositing $12,220 in a month, 6 deposits from a **card in someone else's name**, withdrawn
  to the player's own account (a **U-turn**).
- Recommended action: **Verify who owns the funding card and hold withdrawals to other accounts**.

### 6. Ask the AI (30 s)

On any open alert, **Ask AI** tab → click **What should I check next?**, then ask your own question.
Answers come only from the case's evidence; a number not found in it is flagged under the answer.

### 7. Fraud and identity (60 s)

- `ALR-01348`, **account takeover**: impossible travel (Malta → Southwestern Ontario in 4 minutes), a new
  device, and deposits from a card in another name. Action: **Hold withdrawals and verify the owner**.
- `ALR-02503`, **sanctions screening match** with deposits 3.6× income: action **Hold withdrawals and
  resolve the screening match**.
- `ALR-04566`, the honest counterpart: a **screening match on an otherwise ordinary player**. It must still be
  reviewed, so it's an alert, but **Low confidence** with the mitigating factor stated. This is what
  "whether it truly warrants investigation" looks like.

### 8. Safer Gambling and the AI's contribution (60 s)

- `ALR-03253`: a software developer whose deposits rose **71.9×** on their own history and are far above
  players who usually bet like them. Action: **Safer Gambling outreach**.
- `ALR-00368`: a player whose stake is 12.4× their peers'. The rules alone score this **35**, under the alert
  line; the AI model (over 99%) lifts it to **55**. Without the AI, nobody would see it.

### 9. Network and overview (60 s) — *Bonus 4 and 5*

- `ALR-02309` → **Network** tab: a ring of 6 accounts sharing a device, card and address. Click a circle to
  jump to that account.
- Top bar → **Overview**: queue at a glance, **compliance indicators**, **emerging risk** (transaction flags
  over 13 weeks, with what is rising), the **watchlist** (unusual players below the alert line, found by the
  AI models), the **AI model card with the never-seen-population test**, and the **audit trail** (CSV).

### 10. Does it work? (45 s) — *Requirements 1 and 3 evidence*

Switch to `docs/VALIDATION.md`:

- **96%** of 289 planted risky players alerted; only **0.40%** of normal players flagged (fixed rules: 2.76%,
  with 394 alerts against our 296).
- **High-confidence alerts are all real cases**; every false positive in this population sits in Low confidence.
- **Never-seen populations**: the system, trained on seed 42, catches 96–97% of risky players in two brand-new
  populations, with 0.55–0.66% of normal players flagged.
- Caveat: synthetic data designed by the same team. This shows the pipeline works end to end, not real-world
  accuracy; `docs/DATA_INTEGRATION.md` shows how it would run on real data.

### 11. Close (15 s)

> Explain before you rank: every point is a reason with its numbers, the confidence says how sure we are and
> why it might be innocent, the AI adds evidence it can show, and the investigator always decides.

## If something goes wrong

| Symptom | Fix |
|---|---|
| Banner says "API not reachable … mock data" | The API isn't running. Restart with `-SkipPipeline`. |
| Port 8000 in use | `.\run_demo.ps1 -SkipPipeline -Port 8001` |
| Showcase alert missing | Data was regenerated with another seed or config; rerun the full pipeline with the default config. |
| "Enter your name in the Investigator box" | Type a name top right; decisions are recorded in the audit trail. |
| Summary says "built-in template" | No LLM provider is reachable. Start Ollama or check `.env`; `GET /ai/status` says what it found. |
| AI summary is slow | Local models are slow on first use. Open the showcase alerts once before presenting. |
