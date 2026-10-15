"""Step 4 - Validation against the injected ground truth.

Metrics:
  * recall per injected scenario: share alerted (score >= ALERT_MIN_SCORE), and share
    with a reason of the matching anomaly type (at any score)
  * precision@k (k = 25, 50, 100) for:
      - combined score (rules + peer z-scores + Isolation Forest + supervised model)
      - combined score without the Isolation Forest points
      - combined score without the supervised-model points
      - supervised model probability alone (out-of-fold)
      - legacy rules-only baseline: fixed absolute thresholds with no player context
        (30-day deposits >= $3,000; any single deposit >= $1,000; any transaction from
        outside Ontario; >= 3 bets per day), ranked by rules hit, then deposits
      - random ordering (= prevalence)
  * false-positive rate on normal (non-injected) players
  * effect of the supervised model: recall and false positives with and without its points
  * prioritisation quality: how many distinct scores, largest tie
  * confidence: precision of High / Medium / Low confidence alerts (where the false positives go)
  * watchlist: how many sub-threshold "unusual" players were really risky
  * cross-seed generalisation, from data/scores/cross_seed.json (cross_seed.py)
  * three example false positives with an explanation

Inputs:  data/scores/risk_scores.csv, data/synthetic/scenario_labels.csv,
         data/synthetic/benign_labels.csv, data/features/player_features.parquet,
         data/scores/alerts.json, data/models/model_card.json (optional)
Outputs: data/scores/validation_report.json, docs/VALIDATION.md

Usage:  python backend/pipeline/validate.py
"""
from __future__ import annotations

import json

import pandas as pd

from common import ALERT_MIN_SCORE, BANDS, DOCS, FEATURES, MODELS, SCORES, SYNTH, load_metadata
from detect import score_from_points

KS = [25, 50, 100]
EXPECTED_TYPE = {
    "income_mismatch": "income_mismatch",
    "peer_deviation": "peer_deviation",
    "location_anomaly": "location_anomaly",
    "behaviour_change": "behaviour_change",
    "linked_ring": "linked_players",
    "structuring": "structuring",
    "third_party_funding": "money_movement",
    "dormant_reactivation": "dormant_reactivation",
    "identity_risk": "identity_screening",
}
LEGACY_RULES = {
    "deposits_30d >= $3,000": lambda f: f.deposits_30d >= 3000,
    "single deposit >= $1,000": lambda f: f.max_deposit_30d >= 1000,
    "any transaction outside Ontario": lambda f: f.out_of_province_txns_30d >= 1,
    ">= 3 bets per day": lambda f: f.bets_per_day_30d >= 3,
}
BENIGN_EXPLANATION = {
    "benign_surge": ("a normal player planted with a busy month (more betting days and 1.5-2x stakes in the last "
                     "30 days, 'benign surge'). The own-baseline rules correctly see the change but cannot know it "
                     "is harmless; a light-touch Safer Gambling check-in is still proportionate."),
    "high_roller": ("a high-income player planted with stakes 3-5x their peers' for the whole period ('high "
                    "roller'). No risky behaviour was injected; the flags come from that steady high-stakes play "
                    "plus ordinary month-to-month swings in deposits and losses."),
    "benign_travel": ("a player planted with a trip outside Ontario ('benign travel'). There is no new device and "
                      "no impossible travel, which is what separates it from account takeover."),
    "household": "one of two players in a household sharing an address (planted as 'household').",
    "steady_high_value": ("a high earner planted with a steady history of large deposits ('steady high value'). "
                          "Deposits stay inside the income band; the flags come from the comparison with peers "
                          "plus ordinary month-to-month swings in losses."),
    "screening_false_positive": ("a normal player whose sanctions screening returned a name match that is a false "
                                 "positive ('screening false positive'). Every potential match must be reviewed, so "
                                 "the alert is correct procedure; the confidence is Low because nothing else is unusual."),
    "pep": "a politically exposed person with otherwise ordinary play (planted as 'pep').",
    "unverified_identity": "a normal player whose identity check is still pending (planted as 'unverified identity').",
    "": "a normal player with no planted pattern; the flag comes from ordinary random variation.",
}


def precision_at(order: pd.Series, truth: set, k: int) -> float:
    return round(sum(pid in truth for pid in order.head(k)) / k, 3)


def evaluate() -> dict:
    meta = load_metadata()
    scores = pd.read_csv(SCORES / "risk_scores.csv").fillna({"reason_codes": "", "anomaly_types": "",
                                                              "ml_points": 0, "if_points": 0})
    labels = pd.read_csv(SYNTH / "scenario_labels.csv")
    benign = pd.read_csv(SYNTH / "benign_labels.csv").groupby("player_id").pattern.first()
    feats = pd.read_parquet(FEATURES / "player_features.parquet").set_index("player_id")
    alerts = {a["player_id"]: a for a in json.loads((SCORES / "alerts.json").read_text(encoding="utf-8"))}
    wl_path = SCORES / "watchlist.json"
    watchlist = json.loads(wl_path.read_text(encoding="utf-8")) if wl_path.exists() else []

    s = scores.set_index("player_id")
    injected = set(labels.player_id)
    normal_ids = s.index.difference(list(injected))
    prevalence = len(injected) / len(s)

    # Recall per scenario -------------------------------------------------------------
    recall = {}
    for scen, grp in labels.groupby("scenario"):
        sub = s.loc[grp.player_id]
        typed = sub.anomaly_types.str.split("|").map(lambda ts: EXPECTED_TYPE[scen] in ts)
        recall[scen] = {
            "players": len(sub),
            "recall_alerted": round(float(sub.alert.mean()), 3),
            "recall_type_reason": round(float(typed.mean()), 3),
            "median_score": float(sub.score.median()),
        }
    all_sub = s.loc[list(injected)]
    recall["all_injected"] = {"players": len(all_sub), "recall_alerted": round(float(all_sub.alert.mean()), 3),
                              "recall_type_reason": None, "median_score": float(all_sub.score.median())}

    # Orderings ------------------------------------------------------------------------
    combined = scores.player_id  # detect.py ranks by score, then total points, then AI probability

    def without(points_col: str) -> pd.Series:
        pts = (scores.points_total - scores[points_col]).clip(lower=0)
        return scores.assign(s2=pts.map(score_from_points), p2=pts).sort_values(
            ["s2", "p2", "player_id"], ascending=[False, False, True]).player_id
    no_if = without("if_points")
    f = feats.copy()
    hits = sum(rule(f).astype(int) for rule in LEGACY_RULES.values())
    legacy = (pd.DataFrame({"player_id": f.index, "hits": hits.values, "dep": f.deposits_30d.values})
              .sort_values(["hits", "dep", "player_id"], ascending=[False, False, True]))
    legacy_alerted = set(legacy[legacy.hits > 0].player_id)

    no_ml_score = (scores.points_total - scores.ml_points).clip(lower=0).map(score_from_points)
    no_ml = without("ml_points")
    orderings = {"combined": combined, "combined_without_isolation_forest": no_if,
                 "combined_without_ml_model": no_ml, "legacy_rules_only": legacy.player_id}
    if scores.ml_probability.notna().any():
        orderings["ml_model_only"] = scores.sort_values(["ml_probability", "player_id"],
                                                        ascending=[False, True]).player_id
    precision = {name: {f"p@{k}": precision_at(o, injected, k) for k in KS} for name, o in orderings.items()}
    precision["random"] = {f"p@{k}": round(prevalence, 3) for k in KS}

    alerted = set(s.index[s.alert])
    fp_rate = len(alerted - injected) / len(normal_ids)

    # What the supervised model adds: the same alert rule with and without its points.
    alerted_no_ml = set(scores.player_id[no_ml_score >= ALERT_MIN_SCORE])
    labels_by = labels.groupby("scenario").player_id.agg(set)

    def effect(al: set) -> dict:
        return {"alerts": len(al), "recall_all": round(len(al & injected) / len(injected), 3),
                "false_positive_rate": round(len(al - injected) / len(normal_ids), 4),
                "recall_by_scenario": {k: round(len(al & v) / len(v), 3) for k, v in labels_by.items()}}
    ml_effect = {"with_ml": effect(alerted), "without_ml": effect(alerted_no_ml)}
    card_path = MODELS / "model_card.json"
    model_card = json.loads(card_path.read_text(encoding="utf-8")) if card_path.exists() else None
    legacy_fp_rate = len(legacy_alerted - injected) / len(normal_ids)
    # Sorted so equal counts always list in the same order (set order varies between Python runs).
    fp_patterns = pd.Series([benign.get(p, "") or "none" for p in sorted(alerted - injected)]).value_counts()
    benign_alerts = {k: int(v) for k, v in sorted(fp_patterns.items(), key=lambda kv: (-kv[1], kv[0]))}

    # Example false positives: highest-scoring non-injected alerts, one per pattern where possible.
    fps = scores[scores.alert & ~scores.player_id.isin(injected)].copy()
    fps["pattern"] = fps.player_id.map(benign).fillna("")
    examples = []
    for _, row in fps.sort_values(["score", "player_id"], ascending=[False, True]).iterrows():
        if row.pattern in {e["pattern"] for e in examples} and len(fps.pattern.unique()) >= 3:
            continue
        a = alerts[row.player_id]
        examples.append({"player_id": row.player_id, "score": int(row.score), "band": row.band,
                         "pattern": row.pattern, "reasons": [r["detail"] for r in a["reasons"]],
                         "recommended_action": a["recommended_action"]["action"],
                         "explanation": BENIGN_EXPLANATION.get(row.pattern, BENIGN_EXPLANATION[""])})
        if len(examples) == 3:
            break

    # Prioritisation spread, confidence and watchlist ------------------------------------------
    al = scores[scores.alert]
    spread = {"distinct_scores": int(al.score.nunique()), "largest_tie": int(al.score.value_counts().max()),
              "largest_tie_after_points": int(al.groupby(["score", "points_total"]).size().max()),
              "max_score": int(al.score.max())}
    conf = pd.DataFrame([{"level": a["confidence"]["level"], "hit": pid in injected} for pid, a in alerts.items()])
    confidence_table = {lvl: {"alerts": int(len(g)), "precision": round(float(g.hit.mean()), 3)}
                        for lvl, g in conf.groupby("level")}
    wl = {"players": len(watchlist), "injected": sum(w["player_id"] in injected for w in watchlist),
          "injected_scenarios": pd.Series([labels.set_index("player_id").scenario.get(w["player_id"])
                                           for w in watchlist if w["player_id"] in injected]).value_counts().to_dict()}
    xs_path = SCORES / "cross_seed.json"
    cross_seed = json.loads(xs_path.read_text(encoding="utf-8")) if xs_path.exists() else None

    band_mix = (s.assign(group=["injected" if p in injected else "normal" for p in s.index])
                .groupby(["group", "band"]).size().unstack(fill_value=0))
    report = {
        "dataset": {"players": len(s), "injected": len(injected), "prevalence": round(prevalence, 4),
                    "seed": meta["seed"], "window_end": meta["end_date"]},
        "alert_threshold": ALERT_MIN_SCORE,
        "bands": {name: cut for cut, name in BANDS},
        "alerts": int(s.alert.sum()),
        "recall": recall,
        "precision_at_k": precision,
        "false_positive_rate": {"combined": round(fp_rate, 4), "legacy_rules_only": round(legacy_fp_rate, 4),
                                "combined_false_positives_by_pattern": benign_alerts},
        "legacy_rules": list(LEGACY_RULES),
        "legacy_alerts": len(legacy_alerted),
        "legacy_recall": round(len(legacy_alerted & injected) / len(injected), 3),
        "band_mix": {g: {b: int(v) for b, v in row.items()} for g, row in band_mix.iterrows()},
        "example_false_positives": examples,
        "ml_effect": ml_effect,
        "score_spread": spread,
        "confidence": confidence_table,
        "watchlist": wl,
        "cross_seed": cross_seed,
        "model_card": None if model_card is None else {k: model_card[k] for k in
                                                        ["model", "explainer", "evaluation", "metrics",
                                                         "global_importance"]},
        "checks": {
            "every_type_has_recall": all(scen in recall for scen in EXPECTED_TYPE),
            "high_confidence_alerts_are_reliable": confidence_table.get("High", {}).get("precision", 0) >= 0.95,
            "scores_do_not_pile_up_at_the_top": spread["largest_tie"] <= 0.15 * len(al),
            "combined_beats_rules_only_at_p50":
                precision["combined"]["p@50"] > precision["legacy_rules_only"]["p@50"],
            "ml_model_raises_recall_without_more_false_positives":
                ml_effect["with_ml"]["recall_all"] >= ml_effect["without_ml"]["recall_all"]
                and ml_effect["with_ml"]["false_positive_rate"] <= ml_effect["without_ml"]["false_positive_rate"] + 0.005,
        },
    }
    return report


def pct(x) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def write_markdown(r: dict) -> str:
    ds = r["dataset"]
    lines = [
        "# Validation",
        "",
        "> Generated by `python backend/pipeline/validate.py`. Do not edit by hand; rerun the pipeline instead.",
        "> All numbers are measured on **synthetic data** against the injected ground truth in "
        "`data/synthetic/scenario_labels.csv`.",
        "",
        f"Dataset: {ds['players']:,} players, {ds['injected']} injected risky players "
        f"({ds['prevalence']:.1%}), seed {ds['seed']}, 30-day window ending {ds['window_end']}. "
        f"An alert is a player scoring **{r['alert_threshold']}+** (Medium or above); "
        f"{r['alerts']} players were alerted.",
        "",
        "## Recall per anomaly type",
        "",
        "*Alerted* = scored Medium or above. *Typed reason* = has at least one reason of the matching anomaly "
        "type, at any score.",
        "",
        "| Injected scenario | Players | Alerted | Typed reason | Median score |",
        "|---|---:|---:|---:|---:|",
    ]
    for scen, v in r["recall"].items():
        lines.append(f"| {scen} | {v['players']} | {pct(v['recall_alerted'])} | {pct(v['recall_type_reason'])} "
                     f"| {v['median_score']:.0f} |")
    p = r["precision_at_k"]
    lines += [
        "",
        "## Prioritisation: precision@k",
        "",
        "Share of the top *k* ranked players that are injected risky players.",
        "",
        "| Ordering | p@25 | p@50 | p@100 |",
        "|---|---:|---:|---:|",
    ]
    names = {"combined": "**Combined score** (rules + peer z + behaviour groups + Isolation Forest + AI model)",
             "combined_without_isolation_forest": "Combined without Isolation Forest",
             "combined_without_ml_model": "Combined without the AI model",
             "ml_model_only": "AI model probability alone (out-of-fold)",
             "legacy_rules_only": "Legacy rules only (fixed thresholds, no context)",
             "random": "Random order (= prevalence)"}
    for key, label in names.items():
        if key not in p:
            continue
        lines.append(f"| {label} | {p[key]['p@25']:.0%} | {p[key]['p@50']:.0%} | {p[key]['p@100']:.0%} |")
    fp = r["false_positive_rate"]
    lines += [
        "",
        "Legacy rules: " + "; ".join(r["legacy_rules"]) + ". Ranked by number of rules hit, then 30-day deposits.",
        "",
        "## False positives",
        "",
        "| | Combined score | Legacy rules only |",
        "|---|---:|---:|",
        f"| Normal players alerted | {fp['combined']:.2%} | {fp['legacy_rules_only']:.2%} |",
        f"| Alerts raised | {r['alerts']} | {r['legacy_alerts']} |",
        f"| Injected players caught | {pct(r['recall']['all_injected']['recall_alerted'])} | "
        f"{pct(r['legacy_recall'])} |",
        "",
        "Combined-score false positives by planted benign pattern: "
        + ", ".join(f"{k}: {v}" for k, v in fp["combined_false_positives_by_pattern"].items()) + ".",
        "",
        "### Three example false positives",
        "",
    ]
    for i, e in enumerate(r["example_false_positives"], 1):
        lines += [f"**{i}. {e['player_id']}: score {e['score']} ({e['band']})**", ""]
        lines += [f"- {d}" for d in e["reasons"]]
        lines += ["", f"Recommended action: {e['recommended_action']}.", "",
                  f"Why it is a false positive: this is {e['explanation']}", ""]
    sp, cf, wl = r["score_spread"], r["confidence"], r["watchlist"]
    lines += [
        "## Prioritisation: does the score separate the top of the queue?",
        "",
        "The score is the sum of reason points with two adjustments: flags of the same anomaly type overlap, so "
        "within a type the strongest counts in full and the rest at half; and above 70 points each extra point "
        "counts progressively less (a soft cap), so very strong cases stay ordered instead of all reading 100. "
        "Equal scores are ordered by total points, then the AI model's probability.",
        "",
        f"Alerts use **{sp['distinct_scores']}** distinct scores (highest {sp['max_score']}); the largest group "
        f"sharing one score is **{sp['largest_tie']}** alerts, and **{sp['largest_tie_after_points']}** once total "
        "points break ties.",
        "",
        "## Confidence: does this alert truly warrant investigation?",
        "",
        "Each alert gets a confidence from how many independent kinds of evidence agree, the AI model's probability "
        "and the mitigating factors found (reasons the activity may be innocent, shown on the alert).",
        "",
        "| Confidence | Alerts | Share that are real risky players |",
        "|---|---:|---:|",
    ] + [f"| {lvl} | {cf[lvl]['alerts']} | {pct(cf[lvl]['precision'])} |" for lvl in ["High", "Medium", "Low"] if lvl in cf] + [
        "",
        "## Watchlist: emerging risk below the alert line",
        "",
        f"{wl['players']} players score under {r['alert_threshold']} but the AI models find their pattern very "
        f"unusual (Isolation Forest top 1%) or risk-like (AI model 30%+). **{wl['injected']}** of them are planted "
        "risky players the rules alone missed"
        + (" (" + ", ".join(f"{k}: {v}" for k, v in wl["injected_scenarios"].items()) + ")" if wl["injected_scenarios"] else "")
        + ". They are shown separately so they never crowd the alert queue.",
        "",
    ]
    xs = r.get("cross_seed")
    if xs and xs.get("results"):
        lines += [
            "## Generalisation: new populations the system has never seen",
            "",
            f"The AI model was trained on the seed-{xs['trained_on_seed']} population only. Each row below is a "
            "completely new population (different players and numbers, same kinds of planted risk) scored by that "
            "trained model and the unchanged rules. Built and deleted by `backend/pipeline/cross_seed.py`.",
            "",
            "| Population | Risky players caught | Normal players alerted | Top-100 precision | AI model ROC-AUC | "
            "High/Medium-confidence precision | False positives in Low confidence |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for x in xs["results"]:
            lines.append(f"| seed {x['seed']} (never seen) | {pct(x['recall_all'])} | {x['false_positive_rate']:.2%} | "
                         f"{pct(x['precision_at_100'])} | {x['ml_roc_auc']:.3f} | "
                         f"{pct(x['precision_high_medium_confidence'])} | {x['false_positives_in_low_confidence']} |")
        lines.append("")
    me, mc = r["ml_effect"], r["model_card"]
    lines += [
        "## AI model (supervised)",
        "",
        "A gradient-boosting classifier (scikit-learn `HistGradientBoostingClassifier`) learns which feature "
        "combinations match the labelled scenarios; SHAP explains each player's score. Every player is scored by "
        "a model that never saw them (5-fold out-of-fold), and the result enters the score as one more reason "
        "(`ML_MODEL`: +10 at probability 0.5, +20 at 0.85), so it is explained like every other flag.",
        "",
    ]
    if mc:
        m = mc["metrics"]
        lines += [
            f"Out-of-fold ROC-AUC **{m['roc_auc']:.3f}**, average precision **{m['average_precision']:.3f}**, "
            f"recall at probability 0.5 **{pct(m['recall_at_0.5'])}** with **{m['false_positive_rate_at_0.5']:.2%}** "
            "of normal players above 0.5.",
            "",
            "Most influential features (mean |SHAP|): "
            + ", ".join(g["label"] for g in mc["global_importance"][:6]) + ".",
            "",
        ]
    w, wo = me["with_ml"], me["without_ml"]
    lines += [
        "| Alert rule (score 40+) | Alerts | Injected caught | Normal players alerted | Peer deviation caught |",
        "|---|---:|---:|---:|---:|",
        f"| With the AI model | {w['alerts']} | {pct(w['recall_all'])} | {w['false_positive_rate']:.2%} | "
        f"{pct(w['recall_by_scenario'].get('peer_deviation'))} |",
        f"| Without the AI model | {wo['alerts']} | {pct(wo['recall_all'])} | {wo['false_positive_rate']:.2%} | "
        f"{pct(wo['recall_by_scenario'].get('peer_deviation'))} |",
        "",
    ]
    bm = r["band_mix"]
    lines += [
        "## Band mix",
        "",
        "| Group | Low | Medium | High | Critical |",
        "|---|---:|---:|---:|---:|",
    ] + [f"| {g} | " + " | ".join(str(bm[g].get(b, 0)) for b in ["Low", "Medium", "High", "Critical"]) + " |"
         for g in bm]
    c = r["checks"]
    lines += [
        "",
        "## Thresholds and weights in use",
        "",
        f"Bands: Low 0-39, Medium 40-69, High 70-89, Critical 90-99 (alert at {r['alert_threshold']}+). "
        "Rule thresholds and points live in `THRESHOLDS` and `build_reasons()` in `backend/pipeline/detect.py`; "
        "the peer z threshold is 3.0 (upward deviations only, robust z on a log scale). Compliance indicators use "
        "the $10,000 24-hour total (`LARGE_TRANSACTION_24H`) and deposits of $8,000-$9,999.99 or split deposits "
        "crossing $10,000 (`STRUCTURING`).",
        "",
        "## Checks",
        "",
        f"- Every anomaly type has a recall number: **{'yes' if c['every_type_has_recall'] else 'NO'}**",
        f"- Combined score beats legacy rules on precision@50: "
        f"**{'yes' if c['combined_beats_rules_only_at_p50'] else 'NO'}**",
        f"- The AI model raises recall without adding false positives (within 0.5 points): "
        f"**{'yes' if c['ml_model_raises_recall_without_more_false_positives'] else 'NO'}**",
        f"- High-confidence alerts are at least 95% real risky players: "
        f"**{'yes' if c['high_confidence_alerts_are_reliable'] else 'NO'}**",
        f"- No single score holds more than 15% of alerts: **{'yes' if c['scores_do_not_pile_up_at_the_top'] else 'NO'}**",
        "",
        "## Known limits",
        "",
        "- The data and the detectors were designed by the same team, so these numbers show the pipeline works "
        "end to end; they are not evidence of real-world performance.",
        "- The legacy-rules comparison depends on how many legitimate high-value players the generator plants "
        "(`steady_high_value`, 1% of normal players). These are the players fixed \"deposit over $X\" rules "
        "mis-rank; with none of them, both orderings tie at the top.",
        "- Peer deviation is the hardest type: a single metric far above peers scores 25-40 points on its own, "
        "so some injected players stay just under the alert threshold. Players who barely bet in the current "
        "window cannot be caught by 30-day features at all.",
        "- The AI model learns the planted scenarios, so its scores here are optimistic even out-of-fold: it has "
        "seen other players of the same scenario. In production it would be trained on investigator-confirmed "
        "outcomes and monitored for drift.",
        "",
    ]
    return "\n".join(lines)


def main():
    report = evaluate()
    SCORES.mkdir(parents=True, exist_ok=True)
    (SCORES / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "VALIDATION.md").write_text(write_markdown(report), encoding="utf-8", newline="\n")
    p = report["precision_at_k"]
    print("recall (alerted):", {k: v["recall_alerted"] for k, v in report["recall"].items()})
    print("p@50 combined / legacy:", p["combined"]["p@50"], "/", p["legacy_rules_only"]["p@50"])
    print("false positive rate:", report["false_positive_rate"]["combined"])
    print("checks:", report["checks"])


if __name__ == "__main__":
    main()
