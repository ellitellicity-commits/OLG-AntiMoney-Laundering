"""Step 4: validate detection against the injected ground truth.

Metrics:
    - recall per scenario (player scored >= ALERT_MIN_SCORE), and "typed recall" (the alert also
      carries a reason of the matching anomaly type)
    - precision@k (k = 25, 50, 100, 200) for the combined score, a context-free rules-only baseline
      and Isolation Forest alone
    - false-positive rate on normal players
    - rule x scenario hit matrix (how often each reason code fires per scenario)
    - example false positives with their reasons

Outputs: data/scores/validation_report.json, docs/VALIDATION.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ALERT_MIN_SCORE, ROOT, SCORES_DIR, SYNTHETIC_DIR  # noqa: E402

KS = [25, 50, 100, 200]
SCENARIO_TYPES = {
    "income_mismatch": {"income_mismatch", "cash_cycling"},
    "peer_deviation": {"peer_deviation"},
    "location_anomaly": {"location_anomaly"},
    "behaviour_change": {"behaviour_change"},
    "linked_ring": {"linked_players"},
}


def precision_at_k(order: pd.DataFrame, k: int) -> float:
    return round(float(order.head(k)["is_risky"].mean()), 4)


def evaluate(scores: pd.DataFrame, labels: pd.DataFrame, alerts: list[dict]) -> dict:
    s = scores.merge(labels[["player_id", "scenario"]], on="player_id", how="left")
    s["scenario"] = s["scenario"].fillna("normal")
    s["is_risky"] = s["scenario"] != "normal"
    s["flagged"] = s["score"] >= ALERT_MIN_SCORE
    s["rules_flagged"] = s["rules_only_score"] >= ALERT_MIN_SCORE
    s["types"] = s["anomaly_types"].fillna("").str.split(";")

    recall = {}
    for scen, grp in s[s["is_risky"]].groupby("scenario"):
        typed = grp.apply(lambda r: r["flagged"] and bool(SCENARIO_TYPES[scen] & set(r["types"])), axis=1)
        recall[scen] = {
            "players": int(len(grp)),
            "recall": round(float(grp["flagged"].mean()), 4),
            "typed_recall": round(float(typed.mean()), 4),
            "rules_only_recall": round(float(grp["rules_flagged"].mean()), 4),
            "median_score": float(grp["score"].median()),
        }

    combined = s.sort_values(["score", "iforest_percentile"], ascending=False, kind="mergesort")
    rules = s.sort_values(["rules_only_score", "player_id"], ascending=[False, True], kind="mergesort")
    iforest = s.sort_values("iforest_percentile", ascending=False, kind="mergesort")
    pak = {f"p@{k}": {"combined": precision_at_k(combined, k), "rules_only": precision_at_k(rules, k),
                      "isolation_forest_only": precision_at_k(iforest, k)} for k in KS}

    normal = s[~s["is_risky"]]
    flagged = s[s["flagged"]]
    overall = {
        "players": int(len(s)), "injected_risky": int(s["is_risky"].sum()), "alerts": int(s["flagged"].sum()),
        "alert_precision": round(float(flagged["is_risky"].mean()), 4) if len(flagged) else None,
        "overall_recall": round(float(s.loc[s["is_risky"], "flagged"].mean()), 4),
        "false_positive_rate": round(float(normal["flagged"].mean()), 4),
        "false_positives": int(normal["flagged"].sum()),
        "rules_only_false_positive_rate": round(float(normal["rules_flagged"].mean()), 4),
        "rules_only_alerts": int(s["rules_flagged"].sum()),
        "alert_threshold": ALERT_MIN_SCORE,
    }

    codes = s.assign(code=s["reason_codes"].fillna("").str.split(";")).explode("code")
    codes = codes[codes["code"] != ""]
    totals = s["scenario"].value_counts()
    matrix = (codes.groupby(["code", "scenario"]).size().unstack(fill_value=0) / totals).fillna(0).round(3)
    matrix = matrix.reindex(columns=[c for c in ["income_mismatch", "peer_deviation", "location_anomaly",
                                                 "behaviour_change", "linked_ring", "normal"] if c in matrix.columns])

    band_mix = pd.crosstab(s["scenario"], s["band"]).reindex(columns=["Critical", "High", "Medium", "Low"], fill_value=0)

    by_id = {a["player_id"]: a for a in alerts}
    fps = normal[normal["flagged"]].sort_values("score", ascending=False)
    fp_examples = []
    for pid in fps["player_id"].head(3):
        a = by_id.get(pid)
        if a:
            fp_examples.append({"player_id": pid, "score": a["score"], "band": a["band"],
                                "reasons": [{"code": r["code"], "detail": r["detail"], "points": r["points"]} for r in a["reasons"]]})
    missed = s[s["is_risky"] & ~s["flagged"]].sort_values("score")
    return {
        "overall": overall, "recall_by_scenario": recall, "precision_at_k": pak,
        "rule_hit_rate": matrix.to_dict(orient="index"),
        "band_mix": band_mix.to_dict(orient="index"),
        "false_positive_examples": fp_examples,
        "missed": missed[["player_id", "scenario", "score", "reason_codes"]].fillna("").to_dict(orient="records"),
    }


FP_NOTES = {
    "OPPOSITE_BETTING_LINKED": "This player shares an address or device with a household member and they happened to back opposite "
                               "sides of the same events. The generator deliberately creates such benign households; an investigator "
                               "would close this after checking the relationship and the small stakes.",
    "PEER_DEVIATION": "A naturally heavy bettor at the top of their peer group. Their spend is still consistent with income and "
                      "their own history, which is why no income or behaviour-change reason fired; this is a Medium, not High, alert.",
    "UNEXPECTED_LOCATION": "A normal player on a genuine trip outside Ontario. Travel time was plausible, so no impossible-travel "
                           "reason fired and the score stays in the Medium band.",
    "DEPOSIT_SPIKE": "Deposits rose sharply against a modest personal baseline, but spend stays within the declared income band, "
                     "so no income-mismatch reason fired. A short check of recent activity is enough to close it.",
}
FP_NOTE_PRIORITY = ["OPPOSITE_BETTING_LINKED", "UNEXPECTED_LOCATION", "DEPOSIT_SPIKE", "PEER_DEVIATION"]


def to_markdown(rep: dict) -> str:
    o = rep["overall"]
    L = ["# Validation Report", "",
         "> Generated by `backend/pipeline/validate.py` from synthetic data. Every number below is produced by the script; "
         "re-run the pipeline to refresh it. No real data is used.", "",
         "## Summary", "",
         f"- Players: **{o['players']:,}**, of which **{o['injected_risky']}** have injected risky behaviour.",
         f"- Alerts (score >= {o['alert_threshold']}): **{o['alerts']}**; {o['alert_precision']:.1%} of alerts are injected cases.",
         f"- Overall recall: **{o['overall_recall']:.1%}**.",
         f"- False-positive rate on normal players: **{o['false_positive_rate']:.2%}** ({o['false_positives']} players). "
         f"Context-free rules: {o['rules_only_false_positive_rate']:.2%} ({o['rules_only_alerts']} alerts in total).", "",
         "## Recall per anomaly type", "",
         "| Scenario | Players | Recall | Typed recall* | Rules-only recall | Median score |",
         "|---|---:|---:|---:|---:|---:|"]
    for scen, r in rep["recall_by_scenario"].items():
        L.append(f"| {scen} | {r['players']} | {r['recall']:.0%} | {r['typed_recall']:.0%} | {r['rules_only_recall']:.0%} | {r['median_score']:.0f} |")
    L += ["", "\\* Typed recall: the alert also carries a reason of the matching anomaly type, i.e. it was caught for the right reason.", "",
          "## Precision@k", "",
          "Share of the top-k ranked players who are injected risky cases.", "",
          "| k | Combined score | Rules only (fixed CAD thresholds) | Isolation Forest only |", "|---:|---:|---:|---:|"]
    for k, v in rep["precision_at_k"].items():
        L.append(f"| {k[2:]} | {v['combined']:.0%} | {v['rules_only']:.0%} | {v['isolation_forest_only']:.0%} |")
    L += ["", "The rules-only baseline uses context-free thresholds (deposits >= $10,000 in 30 days, any single deposit >= $3,000, "
          "withdrawals >= $10,000, any activity outside the home region). It never looks at income, peers or the player's own history.", "",
          "## Rule hit rate by scenario", "",
          "Share of players in each scenario on whom the reason code fired.", ""]
    hr = rep["rule_hit_rate"]
    cols = list(next(iter(hr.values())).keys()) if hr else []
    L.append("| Reason code | " + " | ".join(cols) + " |")
    L.append("|---|" + "---:|" * len(cols))
    for code, row in sorted(hr.items()):
        L.append(f"| `{code}` | " + " | ".join(f"{row[c]:.0%}" for c in cols) + " |")
    L += ["", "## Band mix", "", "| Scenario | Critical | High | Medium | Low |", "|---|---:|---:|---:|---:|"]
    for scen, row in rep["band_mix"].items():
        L.append(f"| {scen} | {row['Critical']} | {row['High']} | {row['Medium']} | {row['Low']} |")
    L += ["", "## Example false positives", ""]
    if not rep["false_positive_examples"]:
        L.append("None.")
    for fp in rep["false_positive_examples"]:
        L.append(f"### {fp['player_id']}: score {fp['score']} ({fp['band']})")
        L.append("")
        for r in fp["reasons"]:
            L.append(f"- `{r['code']}` (+{r['points']}): {r['detail']}")
        fired = {r["code"] for r in fp["reasons"]}
        note = next((FP_NOTES[c] for c in FP_NOTE_PRIORITY if c in fired), None)
        if note:
            L += ["", f"**Why it fired:** {note}"]
        L.append("")
    L += ["## Missed injected players", ""]
    if rep["missed"]:
        L += ["| Player | Scenario | Score | Reasons fired |", "|---|---|---:|---|"]
        for m in rep["missed"]:
            L.append(f"| {m['player_id']} | {m['scenario']} | {m['score']} | {m['reason_codes'].replace(';', ', ') or 'none'} |")
    else:
        L.append("None.")
    L.append("")
    return "\n".join(L)


def run(scores_dir: Path = SCORES_DIR, synthetic_dir: Path = SYNTHETIC_DIR, docs_dir: Path = ROOT / "docs") -> dict:
    scores = pd.read_csv(scores_dir / "risk_scores.csv")
    labels = pd.read_csv(synthetic_dir / "scenario_labels.csv")
    with open(scores_dir / "alerts.json", encoding="utf-8") as fh:
        alerts = json.load(fh)
    rep = evaluate(scores, labels, alerts)
    with open(scores_dir / "validation_report.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "VALIDATION.md").write_text(to_markdown(rep), encoding="utf-8")
    return rep


def main():
    rep = run()
    o = rep["overall"]
    print(f"alerts {o['alerts']} | recall {o['overall_recall']:.1%} | FPR {o['false_positive_rate']:.2%}")
    for k, v in rep["precision_at_k"].items():
        print(f"{k}: combined {v['combined']:.0%}  rules-only {v['rules_only']:.0%}  iforest {v['isolation_forest_only']:.0%}")
    for scen, r in rep["recall_by_scenario"].items():
        print(f"  {scen:18s} recall {r['recall']:.0%} typed {r['typed_recall']:.0%} rules-only {r['rules_only_recall']:.0%}")


if __name__ == "__main__":
    main()
