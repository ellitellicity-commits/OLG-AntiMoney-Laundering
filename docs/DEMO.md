# Demo

A repeatable walkthrough of all four challenge requirements, the compliance angle and the AI features.
Everything shown is **synthetic** (seed 42).

## Before the demo

1. From a clean clone, run `.\run_demo.ps1` (Windows) or `./run_demo.sh` (macOS / Linux / Git Bash).
   This creates `.venv`, installs `requirements.txt`, runs the five pipeline steps (about a minute), starts
   the API and opens the dashboard at http://127.0.0.1:8000/app/.
2. If you already ran the pipeline, `.\run_demo.ps1 -SkipPipeline` starts in a few seconds.
3. **Turn on the free AI assistant** (see README, "AI features"). For the demo, Ollama is the safest choice
   because it runs offline: install it, run `ollama pull llama3.2` once, and keep it running. Groq's free tier
   is faster but needs Wi-Fi and a key in `.env`. Without either, every AI panel still works with its
   built-in fallback, but the "Ask" box says the assistant is offline.
4. Warm the AI summaries for the showcase alerts by opening each one once before you present, because a local
   model can take 10–20 s the first time. After that, summaries are cached in `data/ai_cache.json`.
5. Reset recorded decisions before each rehearsal: stop the server, delete `data/decisions.json`, restart.
6. Use a browser window at least 1280 px wide. Keep `docs/VALIDATION.md` open in a second tab.

The showcase alert IDs below are stable for seed 42. If the generator config changes, pick new ones from
`data/scores/alerts.json` (one per team, injected scenario matching the team).

Time limit: **TBD** (check the ThunderHacks rules). The full talk track runs about 7 minutes; for a 5-minute
slot, drop step 7 (linked players) and shorten step 5.

## Talk track and click path

### 1. The problem (30 s)

> Investigators get thousands of rule alerts a day with no reasons and no context. A $5,000 deposit means
> one thing for a steady high earner and another for a student who usually deposits $50.

Point at the header: **SYNTHETIC DATA**, 5,000 players, 180 days of sports betting.

### 2. Prioritisation: the queue, in plain English (45 s) — *Requirement 3*

- The queue is one ranked list across AML, Fraud and Safer Gambling, sorted by the 0–100 score. Each badge
  shows **number + label + 4-segment meter**, so risk never relies on colour alone.
- Type into **Ask the queue**: `critical AML alerts with linked players` → **Find**. The filters set
  themselves and the result line says how the request was read (by the AI model, or by keyword matching
  when no model is running). Click **Clear**.

### 3. AML showcase: `ALR-00635` (90 s) — *Requirements 1, 2, 4*

Press `/`, type `00635`, press `↓` then `Enter`.

- Delivery driver, declared income $20–40k, score **100 Critical**.
- **Case summary** at the top: a plain-language summary written by the AI from the evidence below. Every
  number in it has been checked against the case file; if the model invents a figure, the summary is
  rejected and the template is shown instead.
- *Why flagged*, in order of points:
  - **Deposits far above similar players**: $13,310 in 30 days vs a peer median of $80 (166×).
  - **Average stake far above similar players**: 26.7× the peer median.
  - **Deposits far above declared income**: 5.3× the monthly income estimate, with the declared occupation.
  - **Money in and out with little real betting**: $9,860 withdrawn, only 27% of deposits bet.
  - **AI model: matches known risk patterns**: the gradient-boosting model's probability and its SHAP
    drivers, shown as one more reason with points, never as a black box.
- Peer chart: the solid dot (last 30 days) is far right of the grey peer band; the hollow dot is the
  player's own baseline. This is "contextual risk": compared with themselves **and** with peers.
- Recommended action: **Request source of funds and review for layering** (AML).
- Press `D`, then `Enter` to **Accept recommendation**. The status changes to *In review* in both the
  detail panel and the queue.

### 4. Compliance: structuring, `ALR-00020` (60 s) — *Winning criterion 7*

Search `00020`.

- **Deposits kept just under the $10,000 reporting threshold**: 4 deposits between $8,000 and $9,999.99,
  and 3 times deposits each under $10,000 added up past it within 24 hours (e.g. 2 deposits totalling
  $18,500).
- **$10,000 or more deposited within 24 hours**: the FINTRAC-style 24-hour rule indicator.
- *Recent activity* → **Show flagged only**: each transaction carries its own flags ("Just under $10,000",
  "$10,000+ within 24 hours", "Low-odds bet").
- **Activity over time**: weekly bars show deposits jumping in the last 30 days against the 90-day baseline.
- Click **Case report**: a printable page with the summary, evidence, flagged transactions and decision
  history, ready to attach to a case. (Indicators for review, not a regulatory filing.)

### 5. Ask the AI about a case (45 s)

Still on `ALR-00020`, click the suggestion **What should I check next?**, then type your own question, e.g.
*How does this player compare with similar players?*

- Answers come only from this case's evidence. If an answer contains a number that is not in the evidence,
  it is flagged in orange under the answer ("Check: … not found in the evidence").

### 6. Fraud showcase: `ALR-00077` (45 s)

Search `00077`.

- **Activity from two places too far apart in time**: 6 events, e.g. Ottawa 16:41 → Malta 16:55 (14 min).
- **New device used from outside Ontario** plus a new payment method; 57% of 30-day activity from outside
  Ontario.
- Recommended action: **Hold withdrawals and verify the account owner's identity (possible account
  takeover)**. Press `D`, `Tab` to **Escalate**, `Enter`.

### 7. Safer Gambling showcase: `ALR-00166` (45 s)

Search `00166`.

- Registered nurse, income $80–120k. Deposits of $14,960 are high but there is **no** income-mismatch flag:
  context matters.
- Against their own history: deposits **59.8×**, losses **45.9×**, and **50%** of bets now placed between
  midnight and 6 a.m. (was 3%). The timeline makes the change visible at a glance.
- Recommended action: **Safer Gambling outreach: check in and offer deposit and loss limits**.
- Show **Close as explained…**: the close button refuses an empty reason. Cancel.

### 8. The AI catches what rules miss: `ALR-00404` (30 s)

Search `00404`.

- Police officer whose average stake is 10.8× their peers'. The rules alone score this **34**, under the
  alert line, so a rules-only system would never show it.
- The AI model rates the pattern over 99% likely to match known risk (+20 points), so it reaches the queue
  at **54 Medium** with its reasons attached.

### 9. Bonus: linked players (30 s)

Search `00024`. *Linked players* lists the other accounts in the ring with the shared device, payment method
and address; **Open alert** jumps between them. Recommended action: review the linked accounts as one case.

### 10. Does it work? (45 s) — *Requirements 1 and 3 evidence*

Switch to `docs/VALIDATION.md`:

- Recall per anomaly type: income mismatch, location, behaviour change, structuring and linked rings 100%;
  peer deviation 70% (the weakest, and we say so).
- **The AI model's effect**: with it, 95% of injected players are alerted vs 89% without, and peer-deviation
  recall rises from 45% to 70%, with **no** increase in false positives (0.63% of normal players).
- Precision@50: combined score 100% vs legacy fixed-threshold rules 92%. Legacy rules raise 336 alerts and
  flag 2.9% of normal players; the combined score raises 241 and flags 0.6%.
- Caveat: synthetic data designed by the same team; this shows the pipeline works end to end, not
  real-world accuracy.

### 11. Close (15 s)

> Explain before you rank: every point in the score is a reason with the numbers behind it, the AI only
> ever restates or adds evidence it can show, and the investigator always makes the decision.

## If something goes wrong

| Symptom | Fix |
|---|---|
| Banner says "API not reachable … mock data" | The API isn't running. The dashboard still works on 5 hand-written alerts; restart with `-SkipPipeline`. |
| Port 8000 in use | `.\run_demo.ps1 -SkipPipeline -Port 8001` |
| Showcase alert missing | Data was regenerated with another seed or config; rerun the full pipeline with the default config. |
| Summary says "built-in template" | No LLM provider is reachable. Start Ollama (`ollama serve`) or check the key in `.env`; the API re-checks every minute, and `GET /ai/status` says what it found. |
| AI summary is slow | Local models are slow on first use. Open the showcase alerts once before presenting (summaries are cached). |
