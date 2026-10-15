# Scope

Sports betting only. All data is synthetic.

## Minimum viable demo (must ship)

1. A synthetic dataset of players and betting transactions with known injected risky players.
2. Detection of all four anomaly types: income mismatch, peer deviation, location anomaly, behaviour change.
3. One 0–100 risk score per player from rules + Isolation Forest + peer z-scores, with a list of reasons and their evidence.
4. A FastAPI backend that serves alerts and player detail.
5. An HTML/CSS/JS dashboard with a ranked alert queue, player detail, a "why flagged" list, a peer comparison chart and a recommended action.
6. A validation report: recall per anomaly type and precision@k against the injected labels.

## Stretch (only after the MVP works end to end)

- Jube integration (alerts become Jube cases).
- Network analysis of linked players (shared device, payment method or address). *Built.*
- Gradient-boosting model with SHAP-backed reasons. *Built (scikit-learn, out-of-fold).*
- LLM summary that restates computed evidence only. *Built, with an automatic number check, plus case Q&A and plain-English queue search; free providers only.*
- Activity timeline and case notes. *Timeline built; case notes are the decision notes.*
- Compliance indicators: structuring and the $10,000 24-hour rule, plus per-transaction flags and a printable case report. *Built.*

## How each requirement is demonstrated

| Requirement | What the judges see |
|---|---|
| 1. Detect unusual or suspicious activity | A queue containing all four anomaly types, plus the validation report showing which injected cases were caught |
| 2. Contextual risk assessment | The peer comparison chart and reason lines showing "vs own baseline" and "vs peer median" for each flag |
| 3. Investigation prioritization | The queue sorted by risk score, with precision@k beating a rule-only ordering |
| 4. Investigator experience | Opening one alert: score, reasons, peer chart and recommended action on one screen, then making a decision |

## Not building

- Anything outside sports betting (casino, lottery, iGaming slots).
- Real data, real player identities or connections to OLG systems.
- Login, user accounts, roles or permissions.
- Real-time streaming. Batch scoring is enough.
- Mobile layout.
- Regulatory filing (e.g., generating actual suspicious transaction reports). The case report and compliance indicators support a filing decision; they are not one.
- Model retraining from investigator feedback. (The AI risk model trains on the synthetic scenario labels only.)
- Production deployment, security hardening or scaling.
