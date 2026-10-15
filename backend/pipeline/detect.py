"""Step 3: detection and scoring.

Three detectors feed one explainable 0-100 risk score:
    1. Rules         - clear thresholds per anomaly type, each emitting a reason code
    2. Peer z-scores - robust z within the player's peer group (|z| >= Z_THRESHOLD)
    3. Isolation Forest - overall multivariate unusualness

score = sum of reason points, with each anomaly type capped at TYPE_CAP points, capped at 100.
Every point in the score therefore traces back to a reason with evidence values.

Outputs:
    data/scores/risk_scores.csv   player_id, score, band, team, top_reason_code, anomaly_types,
                                  reason_codes, reason_count, rules_only_score, iforest_percentile
    data/scores/alerts.json       full alert objects (score >= ALERT_MIN_SCORE)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ALERT_MIN_SCORE, FEATURES_DIR, SCORES_DIR, band_for  # noqa: E402

# --------------------------------------------------------------------------------------
# Tunable weights and thresholds (open item #7). Validated in validate.py.
# --------------------------------------------------------------------------------------
WEIGHTS = {
    "type_cap": 50,
    "z_threshold": 3.0,
    "income_ratio_min": 0.5,  # deposits_30d / monthly income
    "iforest_points": [(0.99, 15), (0.97, 10), (0.95, 5)],  # (percentile, points)
}
TEAM_BY_TYPE = {
    "income_mismatch": "AML",
    "cash_cycling": "AML",
    "linked_players": "AML",
    "location_anomaly": "Fraud",
    "behaviour_change": "Safer Gambling",
    "peer_deviation": "AML",  # switched to Safer Gambling when the player is losing heavily
    "multivariate_outlier": "AML",
}
ACTIONS = {
    "income_mismatch": ("Request source-of-funds documentation",
                        "Deposits are well above what the declared income band supports."),
    "cash_cycling": ("Escalate for suspicious-transaction review",
                     "Money is deposited and withdrawn with little genuine betting in between."),
    "linked_players": ("Open a linked-account investigation",
                       "The account shares identifiers with other players and bets against them on the same events."),
    "location_anomaly": ("Verify account owner and hold withdrawals to new payment methods",
                         "Activity from unexpected locations or new devices suggests the account may not be used by its owner."),
    "behaviour_change": ("Safer Gambling check-in: offer deposit limits or a time-out",
                         "Spending and play patterns have escalated sharply against the player's own history."),
    "peer_deviation": ("Review stake pattern against peer group",
                       "Betting is far outside what comparable players do."),
    "peer_deviation_sg": ("Safer Gambling check-in: review affordability",
                          "Betting is far outside comparable players and the player is losing heavily."),
    "multivariate_outlier": ("Analyst review of overall activity profile",
                             "The model finds the combination of behaviours unusual, though no single rule fired strongly."),
}
PEER_LABELS = {
    "deposits_30d": "deposits (30 days)",
    "avg_stake_30d": "average stake",
    "bets_per_day_30d": "bets per day",
    "net_loss_30d": "net loss (30 days)",
    "turnover_30d": "amount staked (30 days)",
    "max_deposit_30d": "largest single deposit",
}
IFOREST_FEATURES = [
    "deposit_to_income", "deposits_30d", "avg_stake_30d", "bets_per_day_30d", "net_loss_30d",
    "withdrawal_to_deposit_30d", "turnover_to_deposit_30d", "deposit_change_ratio", "stake_change_ratio",
    "activity_change_ratio", "night_share_change", "chase_deposits_30d", "share_outside_home_30d",
    "impossible_travel_count_30d", "new_devices_30d", "withdrawals_to_new_pm_30d", "linked_players",
    "opposite_bets_with_linked",
]


def money(x: float) -> str:
    return f"${x:,.0f}" if abs(x) >= 100 else f"${x:,.2f}"


def reason(code, anomaly_type, title, detail, evidence, comparison, points):
    return {"code": code, "anomaly_type": anomaly_type, "title": title, "detail": detail,
            "evidence": {k: (round(float(v), 4) if isinstance(v, (int, float, np.integer, np.floating)) else v)
                         for k, v in evidence.items()},
            "comparison": {k: (None if v is None else round(float(v), 4)) for k, v in comparison.items()},
            "points": int(round(points))}


class PeerLookup:
    def __init__(self, stats: pd.DataFrame):
        self.s = stats.set_index(["peer_group", "feature"])

    def median(self, group, feature):
        try:
            return float(self.s.loc[(group, feature), "median"])
        except KeyError:
            return None


# --------------------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------------------
def rule_reasons(r: pd.Series, peers: PeerLookup, w=WEIGHTS) -> list[dict]:
    out = []
    pg = r["peer_group"]
    pm = lambda f: peers.median(pg, f)  # noqa: E731

    # ---- income mismatch -----------------------------------------------------------
    ratio = r["deposit_to_income"]
    if ratio >= w["income_ratio_min"] and r["deposits_30d"] >= 500:
        pts = 20 if ratio < 1 else (30 if ratio < 2 else (40 if ratio < 4 else 45))
        out.append(reason(
            "INCOME_MISMATCH", "income_mismatch", "Deposits far above declared income",
            f"Deposited {money(r['deposits_30d'])} in the last 30 days, {ratio:.1f}x the estimated monthly income "
            f"of {money(r['monthly_income_estimate'])} for a {r['occupation']} in the {r['income_band']} band.",
            {"deposits_30d": r["deposits_30d"], "monthly_income_estimate": r["monthly_income_estimate"],
             "deposit_to_income": ratio, "income_band": r["income_band"], "occupation": r["occupation"]},
            {"peer_median": pm("deposits_30d"), "own_baseline": r["deposits_baseline_m"]}, pts))

    # ---- cash cycling (AML) ---------------------------------------------------------
    if r["deposits_30d"] >= 1000 and r["withdrawal_to_deposit_30d"] >= 0.6 and r["turnover_to_deposit_30d"] < 1.0:
        out.append(reason(
            "CASH_IN_CASH_OUT", "cash_cycling", "Money in and out with little betting",
            f"Withdrew {r['withdrawal_to_deposit_30d']:.0%} of {money(r['deposits_30d'])} deposited, while only staking "
            f"{r['turnover_to_deposit_30d']:.0%} of deposits.",
            {"deposits_30d": r["deposits_30d"], "withdrawals_30d": r["withdrawals_30d"], "turnover_30d": r["turnover_30d"],
             "withdrawal_to_deposit_30d": r["withdrawal_to_deposit_30d"], "turnover_to_deposit_30d": r["turnover_to_deposit_30d"]},
            {"peer_median": None, "own_baseline": None}, 20))

    # ---- location anomaly -----------------------------------------------------------
    if r["impossible_travel_count_30d"] >= 1:
        n = r["impossible_travel_count_30d"]
        out.append(reason(
            "IMPOSSIBLE_TRAVEL", "location_anomaly", "Transactions from distant places too close together",
            f"{n} pair(s) of consecutive transactions came from locations too far apart to travel between in the time.",
            {"impossible_travel_count_30d": n, "distinct_ip_regions_30d": r["distinct_ip_regions_30d"]},
            {"peer_median": 0, "own_baseline": None}, min(30, 20 + 3 * (n - 1))))
    if r["share_outside_home_30d"] >= 0.15:
        share = r["share_outside_home_30d"]
        abroad = r["share_outside_canada_30d"]
        pts = 10 + (8 if abroad >= 0.1 else 0)
        out.append(reason(
            "UNEXPECTED_LOCATION", "location_anomaly", "Activity outside home region",
            f"{share:.0%} of transactions in the last 30 days came from outside {r['home_region']}"
            + (f", including {abroad:.0%} from outside Canada." if abroad > 0 else "."),
            {"share_outside_home_30d": share, "share_outside_canada_30d": abroad,
             "distinct_ip_regions_30d": r["distinct_ip_regions_30d"], "home_region": r["home_region"]},
            {"peer_median": 0, "own_baseline": None}, pts))
    if r["new_devices_30d"] >= 1 and r["share_outside_home_30d"] >= 0.15:
        out.append(reason(
            "NEW_DEVICE_AWAY", "location_anomaly", "New device appearing with out-of-region activity",
            f"{r['new_devices_30d']} device(s) first seen this month, while {r['share_outside_home_30d']:.0%} of activity "
            f"came from outside {r['home_region']}.",
            {"new_devices_30d": r["new_devices_30d"], "share_outside_home_30d": r["share_outside_home_30d"]},
            {"peer_median": 0, "own_baseline": 0}, 12))
    if r["withdrawals_to_new_pm_30d"] >= 1 and r["new_devices_30d"] >= 1:
        out.append(reason(
            "NEW_DEVICE_NEW_PAYOUT", "location_anomaly", "Withdrawals to a new payment method from a new device",
            f"{r['withdrawals_to_new_pm_30d']} withdrawal(s) went to a payment method first seen this month, "
            f"alongside {r['new_devices_30d']} new device(s).",
            {"withdrawals_to_new_pm_30d": r["withdrawals_to_new_pm_30d"], "new_devices_30d": r["new_devices_30d"],
             "new_payment_methods_30d": r["new_payment_methods_30d"]},
            {"peer_median": 0, "own_baseline": 0}, 20))

    # ---- behaviour change -----------------------------------------------------------
    if r["deposit_change_ratio"] >= 3 and r["deposits_30d"] >= 300:
        k = r["deposit_change_ratio"]
        out.append(reason(
            "DEPOSIT_SPIKE", "behaviour_change", "Deposits sharply up on own history",
            f"Deposited {money(r['deposits_30d'])} in the last 30 days against a usual {money(r['deposits_baseline_m'])} "
            f"per 30 days ({k:.1f}x).",
            {"deposits_30d": r["deposits_30d"], "deposit_change_ratio": k},
            {"peer_median": pm("deposits_30d"), "own_baseline": r["deposits_baseline_m"]}, 20 if k < 6 else 30))
    if r["chase_deposits_30d"] >= 3:
        n = r["chase_deposits_30d"]
        out.append(reason(
            "LOSS_CHASING", "behaviour_change", "Re-depositing straight after losses",
            f"{n} deposits were made within 15 minutes of a losing bet in the last 30 days.",
            {"chase_deposits_30d": n, "net_loss_30d": r["net_loss_30d"]},
            {"peer_median": 0, "own_baseline": r["net_loss_baseline_m"]}, 10 if n < 8 else (20 if n < 15 else 25)))
    if r["night_share_change"] >= 0.2 and r["bet_count_30d"] >= 10:
        out.append(reason(
            "LATE_NIGHT_SHIFT", "behaviour_change", "Play moved to late night",
            f"{r['night_share_30d']:.0%} of bets were placed between midnight and 6am, up from {r['night_share_baseline']:.0%}.",
            {"night_share_30d": r["night_share_30d"], "bet_count_30d": r["bet_count_30d"]},
            {"peer_median": None, "own_baseline": r["night_share_baseline"]}, 12))
    if r["stake_change_ratio"] >= 3 and r["bet_count_30d"] >= 5:
        out.append(reason(
            "STAKE_ESCALATION", "behaviour_change", "Average stake rising",
            f"Average stake is {money(r['avg_stake_30d'])}, {r['stake_change_ratio']:.1f}x the usual {money(r['avg_stake_baseline'])}.",
            {"avg_stake_30d": r["avg_stake_30d"], "stake_change_ratio": r["stake_change_ratio"]},
            {"peer_median": pm("avg_stake_30d"), "own_baseline": r["avg_stake_baseline"]}, 10))

    # ---- linked players -------------------------------------------------------------
    if r["opposite_bets_with_linked"] >= 3:
        n = r["opposite_bets_with_linked"]
        out.append(reason(
            "OPPOSITE_BETTING_LINKED", "linked_players", "Betting against linked accounts",
            f"Placed {n} bets on the opposite side of the same event as an account sharing its device, payment method or address.",
            {"opposite_bets_with_linked": n, "linked_players": r["linked_players"]},
            {"peer_median": 0, "own_baseline": None}, 30 if n < 10 else 40))
    if r["linked_players"] >= 2:
        out.append(reason(
            "LINKED_PLAYERS", "linked_players", "Shares identifiers with several accounts",
            f"Shares {r['shared_identifier_count']} device / payment / address identifier(s) with {r['linked_players']} other players.",
            {"linked_players": r["linked_players"], "shared_identifier_count": r["shared_identifier_count"]},
            {"peer_median": 0, "own_baseline": None}, 10))
    return out


def peer_reasons(r: pd.Series, peers: PeerLookup, w=WEIGHTS) -> list[dict]:
    flagged = []
    for feat, label in PEER_LABELS.items():
        z = r[f"z_{feat}"]
        if z >= w["z_threshold"] and r["bet_count_30d"] >= 3:
            flagged.append((z, feat, label))
    if not flagged:
        return []
    flagged.sort(reverse=True)
    z, feat, label = flagged[0]
    med = peers.median(r["peer_group"], feat)
    val = r[feat]
    times = f" ({val / med:.1f}x the peer median of {money(med)})" if med and med > 0 else ""
    fmt = money if feat != "bets_per_day_30d" else (lambda x: f"{x:.1f}")
    others = ", ".join(lbl for _, _, lbl in flagged[1:])
    pts = min(40, 20 + 6 * (z - w["z_threshold"]) + 4 * (len(flagged) - 1))
    return [reason(
        "PEER_DEVIATION", "peer_deviation", f"{label.capitalize()} far above similar players",
        f"{label.capitalize()} of {fmt(val)}{times if feat != 'bets_per_day_30d' else ''} sits in the top "
        f"{max(1 - r[f'pct_{feat}'], 0.001):.1%} of the peer group ({r['peer_group']}, n={r['peer_group_size']})."
        + (f" Also unusual: {others}." if others else ""),
        {feat: val, "z_score": z, "percentile": r[f"pct_{feat}"], "flagged_features": [f for _, f, _ in flagged],
         "peer_group": r["peer_group"]},
        {"peer_median": med, "own_baseline": None}, pts)]


# --------------------------------------------------------------------------------------
# Isolation Forest
# --------------------------------------------------------------------------------------
def iforest_scores(f: pd.DataFrame, seed: int = 7) -> tuple[pd.Series, pd.DataFrame]:
    X = np.log1p(f[IFOREST_FEATURES].clip(lower=0).astype(float))
    model = IsolationForest(n_estimators=300, contamination="auto", random_state=seed)
    model.fit(X)
    raw = -model.score_samples(X)
    pct = pd.Series(raw, index=f.index).rank(pct=True)
    # population-level robust z for explaining what makes a point unusual
    med = X.median()
    scale = ((X.quantile(0.75) - X.quantile(0.25)) / 1.349).clip(lower=0.1)
    zpop = (X - med) / scale
    return pct, zpop


def iforest_reason(pct: float, zrow: pd.Series, w=WEIGHTS) -> list[dict]:
    pts = next((p for cut, p in w["iforest_points"] if pct >= cut), 0)
    if not pts:
        return []
    top = zrow.sort_values(ascending=False).head(3)
    names = ", ".join(top.index.str.replace("_", " "))
    return [reason(
        "MODEL_OUTLIER", "multivariate_outlier", "Unusual overall activity profile (Isolation Forest)",
        f"The Isolation Forest ranks this player more unusual than {pct:.1%} of all players; the most unusual inputs are {names}.",
        {"iforest_percentile": pct, "top_features": list(top.index)},
        {"peer_median": None, "own_baseline": None}, pts)]


# --------------------------------------------------------------------------------------
# Combination, recommendations
# --------------------------------------------------------------------------------------
def combine(reasons: list[dict], w=WEIGHTS) -> tuple[int, dict]:
    by_type: dict[str, int] = {}
    for rs in reasons:
        by_type[rs["anomaly_type"]] = by_type.get(rs["anomaly_type"], 0) + rs["points"]
    by_type = {k: min(v, w["type_cap"]) for k, v in by_type.items()}
    return int(min(100, sum(by_type.values()))), by_type


def recommend(by_type: dict, r: pd.Series) -> dict:
    ranked = sorted((k for k in by_type if k != "multivariate_outlier"), key=lambda k: -by_type[k]) or ["multivariate_outlier"]
    primary = ranked[0]
    key = primary
    if primary == "peer_deviation" and r["net_loss_30d"] > max(500, r["monthly_income_estimate"] * 0.2):
        key = "peer_deviation_sg"
    team = "Safer Gambling" if key == "peer_deviation_sg" else TEAM_BY_TYPE[primary]
    action, why = ACTIONS[key]
    secondary = []
    for k in ranked[1:]:
        if TEAM_BY_TYPE[k] != team and by_type[k] >= 15:
            secondary.append({"team": TEAM_BY_TYPE[k], "action": ACTIONS[k][0]})
    # player protection overlay: heavy losses relative to income always get a Safer Gambling note
    if team != "Safer Gambling" and r["net_loss_30d"] > r["monthly_income_estimate"] * 0.5 and r["net_loss_30d"] > 500:
        secondary.append({"team": "Safer Gambling", "action": "Check affordability: net losses exceed half of estimated monthly income"})
    seen, uniq = set(), []
    for s in secondary:
        if s["team"] not in seen:
            seen.add(s["team"])
            uniq.append(s)
    return {"action": action, "team": team, "rationale": why, "secondary": uniq, "primary_type": primary}


def summary(r: pd.Series, score: int, band: str, reasons: list[dict], rec: dict) -> str:
    """Template summary that only restates computed evidence (no generated facts)."""
    top = reasons[:2]  # already ordered: primary anomaly type first
    parts = " ".join(x["detail"] for x in top)
    return (f"{r['player_id']} ({r['age_band']}, {r['occupation']}, {r['income_band']}, {r['home_region']}) scores "
            f"{score}/100 ({band}). {parts} Recommended: {rec['action']} ({rec['team']}).")


def rules_only_score(r: pd.Series) -> int:
    """Traditional context-free rules for comparison in validation: fixed CAD thresholds only."""
    s = 0
    s += 40 if r["deposits_30d"] >= 10_000 else 0
    s += 25 if r["max_deposit_30d"] >= 3_000 else 0
    s += 20 if r["withdrawals_30d"] >= 10_000 else 0
    s += 15 if r["share_outside_home_30d"] > 0 else 0
    return min(s, 100)


def score_players(f: pd.DataFrame, stats: pd.DataFrame, w=WEIGHTS) -> tuple[pd.DataFrame, list[dict]]:
    peers = PeerLookup(stats)
    f = f.set_index("player_id", drop=False)
    pct, zpop = iforest_scores(f)
    rows, alerts = [], []
    for pid, r in f.iterrows():
        reasons = rule_reasons(r, peers, w) + peer_reasons(r, peers, w) + iforest_reason(pct[pid], zpop.loc[pid], w)
        score, by_type = combine(reasons, w)
        band = band_for(score)
        rec = recommend(by_type, r) if reasons else {"action": "No action", "team": "", "rationale": "", "secondary": [],
                                                     "primary_type": ""}
        types = [k for k, _ in sorted(by_type.items(), key=lambda kv: -kv[1])]
        # primary anomaly type first so the headline reason matches the assigned team
        reasons.sort(key=lambda x: (x["anomaly_type"] != rec["primary_type"], -x["points"]))
        rows.append({"player_id": pid, "score": score, "band": band, "team": rec["team"],
                     "top_reason_code": reasons[0]["code"] if reasons else "",
                     "anomaly_types": ";".join(types), "reason_codes": ";".join(x["code"] for x in reasons),
                     "reason_count": len(reasons),
                     "rules_only_score": rules_only_score(r), "iforest_percentile": round(float(pct[pid]), 4)})
        if score >= ALERT_MIN_SCORE:
            alerts.append({
                "alert_id": f"A-{pid}", "player_id": pid, "score": score, "band": band, "team": rec["team"],
                "anomaly_types": types, "points_by_type": by_type, "top_reason_code": reasons[0]["code"],
                "status": "open", "created_at": r["reference_date"],
                "profile": {k: r[k] for k in ["age_band", "occupation", "income_band", "home_region", "signup_date"]},
                "peer_group": r["peer_group"], "peer_group_size": int(r["peer_group_size"]),
                "key_metrics": {k: round(float(r[k]), 2) for k in [
                    "deposits_30d", "withdrawals_30d", "turnover_30d", "net_loss_30d", "bet_count_30d",
                    "avg_stake_30d", "deposits_baseline_m", "monthly_income_estimate"]},
                "reasons": reasons, "recommended_action": rec, "summary": summary(r, score, band, reasons, rec),
                "iforest_percentile": round(float(pct[pid]), 4),
            })
    scores = pd.DataFrame(rows).sort_values(["score", "player_id"], ascending=[False, True]).reset_index(drop=True)
    alerts.sort(key=lambda a: (-a["score"], a["player_id"]))
    for i, a in enumerate(alerts, 1):
        a["rank"] = i
    return scores, alerts


def run(features_dir: Path = FEATURES_DIR, out_dir: Path = SCORES_DIR, w=WEIGHTS):
    f = pd.read_parquet(features_dir / "player_features.parquet")
    stats = pd.read_parquet(features_dir / "peer_stats.parquet")
    scores, alerts = score_players(f, stats, w)
    out_dir.mkdir(parents=True, exist_ok=True)
    scores.to_csv(out_dir / "risk_scores.csv", index=False)
    with open(out_dir / "alerts.json", "w", encoding="utf-8") as fh:
        json.dump(alerts, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return scores, alerts


def main():
    scores, alerts = run()
    print(f"scored {len(scores):,} players; alerts (score >= {ALERT_MIN_SCORE}): {len(alerts):,}")
    print(scores["band"].value_counts().reindex(["Critical", "High", "Medium", "Low"]).to_string())
    print(f"written to {SCORES_DIR}")


if __name__ == "__main__":
    main()
