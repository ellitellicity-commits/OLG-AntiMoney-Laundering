# Product

<!-- impeccable:product-schema 1 -->

> Written from the team's planning brief without a live interview. Items marked *(inferred)* came from the brief, not from a confirmed answer. Items marked **TBD** are undecided. Check both before relying on them.

## Platform

web

## Stack

Confirmed by the team:

- **Backend:** Python, FastAPI
- **Frontend:** plain HTML, CSS and JavaScript (no framework)
- **Alerting and case management:** Jube (open-source transaction monitoring / case management)
- **Detection:** rules + Isolation Forest + peer-group z-scores. Optional: LightGBM or XGBoost with SHAP explanations. Optional: LLM-written summaries that may only restate evidence the system has already computed.
- Components connect through HTTP APIs.

Deployment target: **TBD** (assumed local laptop demo for the hackathon *(inferred)*).

## Users

Primary users are **OLG investigators** in three teams:

| Team | What they look for | What they need from an alert |
|---|---|---|
| **AML (Anti-Money Laundering)** | Money moving through betting accounts to disguise its source: deposits out of line with income, cash-in/cash-out with little real betting, linked accounts | Evidence strong enough to justify escalation or a suspicious-transaction review |
| **Fraud** | Account takeover, identity misuse, unexpected locations or devices, collusion between linked players | Fast confirmation of whether the account owner is really the one betting |
| **Safer Gambling** | Players whose behaviour is changing in ways that suggest harm: rising stakes, chasing losses, spending beyond their means | Context on how far the player has moved from their own history and from peers, so outreach is proportionate |

**Situation:** each investigator reviews a large number of alerts every day. Time per alert is short, and every decision has to be defensible to a supervisor or regulator. Their questions are: *"Is this worth my time? Why was it flagged? What should I do next?"*

**Secondary audience:** ThunderHacks 2026 judges evaluating the OLG sponsor challenge *(inferred)*.

## Product Purpose

A sports-betting risk-review tool that **finds unusual player behaviour, judges it in context, ranks it, and explains it.**

Rule-based monitoring produces lots of alerts with no reasons attached. Investigators waste time on noise and can't easily see why an alert fired. This product replaces "an alert fired" with "here is how risky this is, here is the evidence, here is how it compares to the player's history and to similar players, and here is a suggested next step."

**Success** means meeting the four judged requirements of the OLG challenge *"Intelligent Player Protection & Fraud Detection"*:

| # | Requirement | Success criterion for this product |
|---|---|---|
| 1 | Detect unusual or suspicious activity | All four anomaly types (below) are detected on synthetic data, with recall measured against injected ground truth |
| 2 | Contextual risk assessment (profile, history, peer groups) | Every flag compares the player against their own baseline **and** their peer group, and shows both numbers |
| 3 | Investigation prioritization | Alerts arrive as a ranked queue with a 0–100 risk score. The highest-ranked alerts contain more true injected cases than a random or rule-only ordering (measured by precision@k) |
| 4 | Investigator experience | Each alert shows its score, a plain-language "why flagged" list backed by evidence values, a peer comparison and a recommended action, and an investigator can reach a decision without leaving the dashboard |

## Positioning

Most monitoring tools say *that* an alert fired. This one says **why**, in context: every flag is tied to the player's own history and to a defined peer group, and each reason comes with the numbers behind it. Any AI-written text may only restate computed evidence and never invents facts.

## Operating Context

- **Scope:** sports betting only. No casino, lottery or other OLG products.
- **Data:** no real OLG data. The challenge provides no datasets, so all players, bets, deposits, withdrawals, devices and locations are **synthetic**, generated with known injected risky behaviour so detection can be validated.
- **Workflow:** alert generated → ranked in queue → investigator opens player detail → reviews reasons, peer comparison, history and linked players → takes the recommended action or overrides it → case tracked in Jube.
- **Environment:** desktop browser on a work machine, used for long review sessions *(inferred)*.

## Capabilities and Constraints

**Anomaly types the product must detect:**

1. **Income mismatch:** spend inconsistent with the player's stated occupation or income band.
2. **Peer deviation:** behaviour that differs significantly from comparable peers.
3. **Location anomaly:** transactions from unexpected locations (new region, impossible travel, or out of province).
4. **Behaviour change:** significant change against the player's own history.

**Bonus capabilities (stretch):** synthetic risky-player data, validation of detection rules, automated investigator recommendations, network analysis of linked players (shared device, payment method or address), and a unified risk dashboard.

**Terminology:**

- *Alert*: one flagged player with one risk score.
- *Reason*: one triggered signal with its evidence values.
- *Peer group*: players with a similar profile (definition draft in `docs/WORKFLOW.md`).
- *Risk band*: Low (0–39) / Medium (40–69) / High (70–100). Three bands, set by the dashboard brief; the cut-offs are still a draft until validation.

**Constraints:**

- The OLG challenge brief is confidential and for registered participants only. Do not publish it.
- Every score must be explainable. No black-box score is shown without reasons.
- LLM output is optional and limited to summarising computed evidence.

**Undecided (TBD):** peer-group definition, risk-band thresholds, score weighting, Jube integration method, deployment target, demo length.

## Brand Commitments

- Tone: **calm, serious, evidence-first**, like a regulatory tool. It must not look like a gambling site.
- Colour is never the only signal. A risk level always shows a number and a text label.
- High contrast.
- **Anti-references:** flashy casino styling (gold, neon, chips, slot imagery); the generic AI-dashboard look (purple gradients, glowing cards, sparkles, vanity KPI tiles).

## Evidence on Hand

- No real data, customers, testimonials or OLG endorsements. **Do not fabricate any.**
- All data shown in the product is synthetic and must be labelled as synthetic in the demo.
- Validation metrics will come from `validate.py` (see `docs/WORKFLOW.md`). Quote only numbers it actually produced.

## Product Principles

1. **Explain before you rank.** A score without reasons is not shown.
2. **Context is the signal.** Every flag is relative to the player's history or a peer group, never a raw threshold alone.
3. **The investigator decides.** The tool recommends; the human acts, and can override with a recorded reason.
4. **Evidence, not narrative.** Generated text may only restate computed facts.
5. **Calm under volume.** The interface is built for the hundredth alert of the day, not the first.

## Accessibility & Inclusion

- Target WCAG 2.2 AA contrast *(inferred from "high contrast")*.
- Risk is shown by number + label (+ shape), never by colour alone.
- Full keyboard navigation of the alert queue *(inferred: high-volume daily use)*.
