"""Step 3 - Detection and scoring.

Four detectors feed one explainable 0-100 risk score:
  1. Rules        clear thresholds per anomaly type, each emitting a reason code
                  (including FINTRAC-style compliance indicators: $10,000 within 24 hours
                  and structuring just under it)
  2. Peer z-score robust z within the player's peer group (|z| > PEER_Z, upward only)
  3. Isolation Forest  overall unusualness across all features (unsupervised)
  4. Supervised model  gradient boosting trained on the labelled scenarios, scored
                  out-of-fold, explained with SHAP (train_model.py; skipped if not run)

Every detector hit becomes a *reason* with evidence values, a comparison against
the player's own baseline and/or peer median, and the points it adds. The score is
the sum of reason points, capped at 100, so the reason list always explains it.

Outputs:
  data/scores/risk_scores.csv  one row per player (all players, alert or not)
  data/scores/alerts.json      full alert objects for players scoring >= ALERT_MIN_SCORE

Thresholds and points below were tuned in step 4 (see docs/VALIDATION.md).

Usage:  python backend/pipeline/detect.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from common import (ALERT_MIN_SCORE, FEATURE_LABEL, FEATURES, NEAR_THRESHOLD, REPORTING_THRESHOLD, SCORES, band_for,
                    load_metadata, symlog)

SEED = 42

THRESHOLDS = {
    "income_ratio": 2.5,          # deposits_30d / monthly income estimate
    "cash_withdraw_ratio": 0.5,   # withdrawals / deposits ...
    "cash_turnover_max": 0.6,     # ... with turnover below this share of deposits
    "cash_min_deposits": 1000,
    "peer_z": 3.0,
    "deposit_surge": 3.0,         # deposits_30d / own baseline per 30 days
    "deposit_surge_min": 500,
    "stake_escalation": 2.5,      # avg stake / own baseline avg stake
    "stake_min_bets": 5,
    "night_shift": 0.25,          # increase in share of bets placed 00:00-05:59
    "night_min_bets": 10,
    "loss_chasing": 3.0,          # net loss / own baseline net loss per 30 days
    "loss_min": 500,
    "out_of_province_min_txns": 1,
    "linked_cluster_min": 3,      # households of 2 sharing an address are not flagged
    "if_pct": 0.975,              # Isolation Forest percentile for a reason
    "if_pct_high": 0.99,
    "near_threshold_min": 2,      # deposits of $8,000-$9,999.99 in 30 days
    "ml_prob": 0.5,               # supervised model probability for a reason
    "ml_prob_high": 0.85,
}

TYPE_LABEL = {
    "income_mismatch": "Income mismatch",
    "peer_deviation": "Peer deviation",
    "location_anomaly": "Location anomaly",
    "behaviour_change": "Behaviour change",
    "money_movement": "Money movement",
    "linked_players": "Linked players",
    "structuring": "Structuring",
    "reporting_threshold": "Reporting threshold",
    "overall_pattern": "Overall pattern",
    "ml_pattern": "AI risk model",
}

# code: (anomaly_type, team, title)
REASONS = {
    "INCOME_MISMATCH": ("income_mismatch", "AML", "Deposits far above declared income"),
    "CASH_IN_CASH_OUT": ("money_movement", "AML", "Money in and out with little real betting"),
    "PEER_DEPOSITS": ("peer_deviation", "AML", "Deposits far above similar players"),
    "PEER_STAKE": ("peer_deviation", "AML", "Average stake far above similar players"),
    "PEER_BET_FREQUENCY": ("peer_deviation", "Safer Gambling", "Bets far more often than similar players"),
    "PEER_NET_LOSS": ("peer_deviation", "Safer Gambling", "Losses far above similar players"),
    "IMPOSSIBLE_TRAVEL": ("location_anomaly", "Fraud", "Activity from two places too far apart in time"),
    "OUT_OF_PROVINCE": ("location_anomaly", "Fraud", "Activity from outside Ontario"),
    "NEW_DEVICE_OUTSIDE_ONTARIO": ("location_anomaly", "Fraud", "New device used from outside Ontario"),
    "DEPOSIT_SURGE": ("behaviour_change", "Safer Gambling", "Deposits sharply up on own history"),
    "STAKE_ESCALATION": ("behaviour_change", "Safer Gambling", "Stakes sharply up on own history"),
    "NIGHT_PLAY_SHIFT": ("behaviour_change", "Safer Gambling", "Betting has moved to late night"),
    "LOSS_CHASING": ("behaviour_change", "Safer Gambling", "Losses sharply up on own history"),
    "LINKED_PLAYERS": ("linked_players", "AML", "Shares devices or payment methods with other accounts"),
    "STRUCTURING": ("structuring", "AML", "Deposits kept just under the $10,000 reporting threshold"),
    "LARGE_TRANSACTION_24H": ("reporting_threshold", "AML", "$10,000 or more deposited within 24 hours"),
    "ISOLATION_FOREST": ("overall_pattern", None, "Unusual overall pattern"),
    "ML_MODEL": ("ml_pattern", None, "AI model: matches known risk patterns"),
}

PEER_METRICS = {  # code: (feature, baseline feature, label, money?)
    "PEER_DEPOSITS": ("deposits_30d", "deposits_base_30d", "deposits in 30 days", True),
    "PEER_STAKE": ("avg_stake_30d", "avg_stake_base", "average stake", True),
    "PEER_BET_FREQUENCY": ("bets_per_day_30d", "bets_per_day_base", "bets per day", False),
    "PEER_NET_LOSS": ("net_loss_30d", "net_loss_base_30d", "net loss in 30 days", True),
}

IF_FEATURES = [
    "deposits_30d", "avg_stake_30d", "bets_per_day_30d", "net_loss_30d", "deposit_income_ratio",
    "deposit_change_ratio", "stake_change_ratio", "loss_change_ratio", "night_share_30d",
    "night_share_change", "withdrawal_to_deposit_ratio", "turnover_to_deposit_ratio",
    "distinct_ip_regions_30d", "share_outside_ontario_30d", "impossible_travel_count_30d",
    "new_devices_30d", "new_payment_methods_30d", "shared_identifier_count",
]
IF_LABEL = FEATURE_LABEL
MONEY_FEATURES = {"deposits_30d", "avg_stake_30d", "net_loss_30d", "max_deposit_30d", "max_deposits_24h_30d"}
RATIO_FEATURES = {"night_share_30d", "night_share_change", "share_outside_ontario_30d",
                  "withdrawal_to_deposit_ratio", "turnover_to_deposit_ratio"}
MULTIPLE_FEATURES = {"deposit_income_ratio", "deposit_change_ratio", "stake_change_ratio", "loss_change_ratio"}


def money(x: float) -> str:
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def rnd(x, nd=2):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def scaled(base: float, value: float, threshold: float, per_unit: float, cap: float) -> int:
    return int(round(min(cap, base + per_unit * max(0.0, value - threshold))))


def feature_value(feat: str, v: float) -> str:
    if feat in MONEY_FEATURES:
        return money(v)
    if feat in RATIO_FEATURES:
        return f"{v:.0%}"
    if feat in MULTIPLE_FEATURES:
        return f"{v:.1f}x"
    if feat.startswith("z_"):
        return f"z = {v:.1f}"
    return f"{v:.1f}" if abs(v - round(v)) > 1e-9 else f"{int(round(v))}"


def make_reason(code: str, detail: str, evidence: dict, comparison: dict, points: int) -> dict:
    anomaly_type, team, title = REASONS[code]
    return {"code": code, "anomaly_type": anomaly_type, "team": team, "title": title, "detail": detail,
            "evidence": evidence, "comparison": comparison, "points": int(points)}


# --- Isolation Forest -------------------------------------------------------------

def isolation_forest(f: pd.DataFrame) -> pd.DataFrame:
    x = pd.DataFrame({c: symlog(f[c]) for c in IF_FEATURES}, index=f.index)
    model = IsolationForest(n_estimators=300, contamination="auto", random_state=SEED).fit(x)
    raw = -model.score_samples(x)  # higher = more unusual
    pct = pd.Series(raw, index=f.index).rank(pct=True)
    # Explain with the features furthest above the population (robust z, upward only).
    med = x.median()
    scale = ((x.quantile(0.75) - x.quantile(0.25)) / 1.349).clip(lower=0.25)
    pop_z = ((x - med) / scale).to_numpy()
    order = np.argsort(-pop_z, axis=1)[:, :3]
    top = [[IF_FEATURES[j] for j in row if pop_z[i, j] > 2] for i, row in enumerate(order)]
    return pd.DataFrame({"if_score": raw, "if_percentile": pct, "if_top_features": top}, index=f.index)


# --- Reasons ------------------------------------------------------------------------

def build_reasons(r, peer_median) -> list[dict]:
    t = THRESHOLDS
    out = []

    # Income mismatch
    if r.deposit_income_ratio >= t["income_ratio"]:
        out.append(make_reason(
            "INCOME_MISMATCH",
            f"{money(r.deposits_30d)} deposited in 30 days, {r.deposit_income_ratio:.1f}x the monthly income "
            f"estimate of {money(r.monthly_income_estimate)} (declared occupation {r.occupation}, "
            f"income band {r.income_band}/yr).",
            {"deposits_30d": rnd(r.deposits_30d), "income_band": r.income_band, "occupation": r.occupation,
             "monthly_income_estimate": rnd(r.monthly_income_estimate),
             "deposit_income_ratio": rnd(r.deposit_income_ratio)},
            {"peer_median": rnd(peer_median(r.peer_group, "deposits_30d")), "own_baseline": rnd(r.deposits_base_30d)},
            scaled(30, r.deposit_income_ratio, t["income_ratio"], 2, 45)))

    # Money movement (AML pattern)
    if (r.deposits_30d >= t["cash_min_deposits"] and r.withdrawal_to_deposit_ratio >= t["cash_withdraw_ratio"]
            and r.turnover_to_deposit_ratio <= t["cash_turnover_max"]):
        out.append(make_reason(
            "CASH_IN_CASH_OUT",
            f"{money(r.deposits_30d)} deposited and {money(r.withdrawals_30d)} withdrawn in 30 days, "
            f"but only {money(r.turnover_30d)} was bet ({r.turnover_to_deposit_ratio:.0%} of deposits).",
            {"deposits_30d": rnd(r.deposits_30d), "withdrawals_30d": rnd(r.withdrawals_30d),
             "turnover_30d": rnd(r.turnover_30d), "turnover_to_deposit_ratio": rnd(r.turnover_to_deposit_ratio)},
            {"own_baseline": rnd(r.deposits_base_30d)},
            25))

    # Compliance indicators (FINTRAC-style; indicators only, not a reporting decision)
    if r.split_threshold_events_30d >= 1 or r.near_threshold_deposits_30d >= t["near_threshold_min"]:
        parts = []
        if r.split_threshold_events_30d >= 1:
            parts.append(f"{int(r.split_threshold_events_30d)} time(s) in 30 days, deposits each under "
                         f"{money(REPORTING_THRESHOLD)} added up to {money(REPORTING_THRESHOLD)} or more within "
                         f"24 hours")
        if r.near_threshold_deposits_30d >= 1:
            parts.append(f"{int(r.near_threshold_deposits_30d)} deposit(s) between {money(NEAR_THRESHOLD)} and "
                         f"{money(REPORTING_THRESHOLD - 0.01)}")
        detail = "; ".join(parts)
        out.append(make_reason(
            "STRUCTURING",
            detail[0].upper() + detail[1:] + (f". Largest: {r.threshold_24h_example}." if r.threshold_24h_example else "."),
            {"split_threshold_events_30d": int(r.split_threshold_events_30d),
             "near_threshold_deposits_30d": int(r.near_threshold_deposits_30d),
             "max_deposits_24h_30d": rnd(r.max_deposits_24h_30d), "example": r.threshold_24h_example},
            {"own_baseline": rnd(r.deposits_base_30d), "peer_median": rnd(peer_median(r.peer_group, "deposits_30d"))},
            scaled(30, r.split_threshold_events_30d + r.near_threshold_deposits_30d, 1, 4, 45)))
    if r.threshold_24h_events_30d >= 1:
        out.append(make_reason(
            "LARGE_TRANSACTION_24H",
            f"{int(r.threshold_24h_events_30d)} episode(s) in 30 days where deposits within 24 hours totalled "
            f"{money(REPORTING_THRESHOLD)} or more (24-hour rule). Largest: {r.threshold_24h_example}.",
            {"threshold_24h_events_30d": int(r.threshold_24h_events_30d),
             "max_deposits_24h_30d": rnd(r.max_deposits_24h_30d), "example": r.threshold_24h_example},
            {"own_baseline": rnd(r.deposits_base_30d)},
            10))

    # Peer deviation
    for code, (feat, base_feat, label, is_money) in PEER_METRICS.items():
        z = getattr(r, f"z_{feat}")
        if z > t["peer_z"]:
            value, med, base = getattr(r, feat), peer_median(r.peer_group, feat), getattr(r, base_feat)
            fmt = money if is_money else (lambda v: f"{v:.2f}")
            multiple = f", {value / med:.1f}x the peer median" if med and med > 0 else ""
            out.append(make_reason(
                code,
                f"{label.capitalize()}: {fmt(value)} vs peer median {fmt(med)}{multiple} "
                f"(z = {z:.1f}, peer group {r.peer_group}).",
                {feat: rnd(value), "peer_z": rnd(z), "peer_group": r.peer_group},
                {"peer_median": rnd(med), "own_baseline": rnd(base)},
                scaled(25, z, t["peer_z"], 5, 40)))

    # Location
    if r.impossible_travel_count_30d >= 1:
        out.append(make_reason(
            "IMPOSSIBLE_TRAVEL",
            f"{int(r.impossible_travel_count_30d)} pair(s) of transactions too close in time for the distance, "
            f"e.g. {r.impossible_travel_example}.",
            {"impossible_travel_count_30d": int(r.impossible_travel_count_30d),
             "example": r.impossible_travel_example},
            {"own_baseline": 0},
            scaled(30, r.impossible_travel_count_30d, 1, 2, 40)))
    if r.out_of_province_txns_30d >= t["out_of_province_min_txns"]:
        out.append(make_reason(
            "OUT_OF_PROVINCE",
            f"{int(r.out_of_province_txns_30d)} transactions ({r.share_outside_ontario_30d:.0%} of 30-day activity) "
            f"from outside Ontario; home region {r.home_region}; {int(r.distinct_ip_regions_30d)} distinct locations.",
            {"out_of_province_txns_30d": int(r.out_of_province_txns_30d),
             "share_outside_ontario_30d": rnd(r.share_outside_ontario_30d),
             "distinct_ip_regions_30d": int(r.distinct_ip_regions_30d), "home_region": r.home_region},
            {"peer_median": rnd(peer_median(r.peer_group, "distinct_ip_regions_30d"))},
            scaled(15, r.share_outside_ontario_30d, 0, 20, 30)))
    if r.new_devices_outside_ontario_30d >= 1:
        out.append(make_reason(
            "NEW_DEVICE_OUTSIDE_ONTARIO",
            f"{int(r.new_devices_outside_ontario_30d)} device(s) first seen in the last 30 days and used from "
            f"outside Ontario; {int(r.new_payment_methods_30d)} new payment method(s).",
            {"new_devices_outside_ontario_30d": int(r.new_devices_outside_ontario_30d),
             "new_devices_30d": int(r.new_devices_30d), "new_payment_methods_30d": int(r.new_payment_methods_30d)},
            {"own_baseline": 0},
            15))

    # Behaviour change vs own baseline
    if r.deposit_change_ratio >= t["deposit_surge"] and r.deposits_30d >= t["deposit_surge_min"]:
        out.append(make_reason(
            "DEPOSIT_SURGE",
            f"{money(r.deposits_30d)} deposited in 30 days vs {money(r.deposits_base_30d)} per 30 days over the "
            f"previous 90 ({r.deposit_change_ratio:.1f}x).",
            {"deposits_30d": rnd(r.deposits_30d), "deposit_change_ratio": rnd(r.deposit_change_ratio)},
            {"own_baseline": rnd(r.deposits_base_30d), "peer_median": rnd(peer_median(r.peer_group, "deposits_30d"))},
            scaled(20, min(r.deposit_change_ratio, 20), t["deposit_surge"], 1, 30)))
    if r.stake_change_ratio >= t["stake_escalation"] and r.bets_30d >= t["stake_min_bets"]:
        out.append(make_reason(
            "STAKE_ESCALATION",
            f"Average stake {money(r.avg_stake_30d)} vs {money(r.avg_stake_base)} over the previous 90 days "
            f"({r.stake_change_ratio:.1f}x) across {int(r.bets_30d)} bets.",
            {"avg_stake_30d": rnd(r.avg_stake_30d), "stake_change_ratio": rnd(r.stake_change_ratio),
             "bets_30d": int(r.bets_30d)},
            {"own_baseline": rnd(r.avg_stake_base), "peer_median": rnd(peer_median(r.peer_group, "avg_stake_30d"))},
            15))
    if r.night_share_change >= t["night_shift"] and r.bets_30d >= t["night_min_bets"]:
        out.append(make_reason(
            "NIGHT_PLAY_SHIFT",
            f"{r.night_share_30d:.0%} of bets placed between midnight and 6 a.m., up from "
            f"{r.night_share_base:.0%} over the previous 90 days.",
            {"night_share_30d": rnd(r.night_share_30d), "night_share_change": rnd(r.night_share_change)},
            {"own_baseline": rnd(r.night_share_base), "peer_median": rnd(peer_median(r.peer_group, "night_share_30d"))},
            15))
    if r.loss_change_ratio >= t["loss_chasing"] and r.net_loss_30d >= t["loss_min"]:
        out.append(make_reason(
            "LOSS_CHASING",
            f"Net loss of {money(r.net_loss_30d)} in 30 days vs {money(max(r.net_loss_base_30d, 0))} per 30 days "
            f"over the previous 90 ({r.loss_change_ratio:.1f}x).",
            {"net_loss_30d": rnd(r.net_loss_30d), "loss_change_ratio": rnd(r.loss_change_ratio)},
            {"own_baseline": rnd(r.net_loss_base_30d), "peer_median": rnd(peer_median(r.peer_group, "net_loss_30d"))},
            15))

    # Network
    if r.network_cluster_size >= t["linked_cluster_min"]:
        out.append(make_reason(
            "LINKED_PLAYERS",
            f"Linked to {int(r.network_cluster_size) - 1} other accounts (cluster {r.network_cluster_id}) through "
            f"{int(r.shared_identifier_count)} shared device, payment method or address identifiers.",
            {"network_cluster_id": r.network_cluster_id, "network_cluster_size": int(r.network_cluster_size),
             "shared_identifier_count": int(r.shared_identifier_count),
             "linked_player_count": int(r.linked_player_count)},
            {"peer_median": 0},
            scaled(25, r.network_cluster_size, t["linked_cluster_min"], 5, 40)))

    # Isolation Forest
    if r.if_percentile >= t["if_pct"]:
        feats = r.if_top_features
        names = ", ".join(IF_LABEL[c] for c in feats) if feats else "a combination of features"
        out.append(make_reason(
            "ISOLATION_FOREST",
            f"More unusual overall than {r.if_percentile:.1%} of players (Isolation Forest); "
            f"most unusual: {names}.",
            {"if_percentile": rnd(r.if_percentile, 4), "if_score": rnd(r.if_score, 4),
             "top_features": {c: rnd(getattr(r, c)) for c in feats}},
            {},
            15 if r.if_percentile >= t["if_pct_high"] else 10))

    # Supervised model (out-of-fold probability + SHAP drivers)
    if not pd.isna(r.ml_probability) and r.ml_probability >= t["ml_prob"]:
        drv = json.loads(r.ml_drivers or "[]")
        names = "; ".join(f"{d['label']} {feature_value(d['feature'], d['value'])}" for d in drv)
        likely = "over 99%" if r.ml_probability > 0.99 else f"{r.ml_probability:.0%}"
        out.append(make_reason(
            "ML_MODEL",
            f"A gradient-boosting model trained on labelled risk scenarios rates this player's pattern "
            f"{likely} likely to match known risky behaviour (scored without seeing this player). "
            f"Biggest drivers (SHAP): {names or 'a combination of features'}.",
            {"ml_probability": rnd(r.ml_probability, 4),
             "drivers": {d["feature"]: d["value"] for d in drv}},
            {},
            20 if r.ml_probability >= t["ml_prob_high"] else 10))

    return sorted(out, key=lambda x: -x["points"])


# --- Recommendations ------------------------------------------------------------------

def recommend(reasons: list[dict], r) -> dict:
    codes = {x["code"] for x in reasons}
    top = next((x for x in reasons if x["team"]), reasons[0])
    sg_codes = codes & {"DEPOSIT_SURGE", "STAKE_ESCALATION", "NIGHT_PLAY_SHIFT", "LOSS_CHASING",
                        "PEER_NET_LOSS", "PEER_BET_FREQUENCY"}
    if {"IMPOSSIBLE_TRAVEL", "NEW_DEVICE_OUTSIDE_ONTARIO"} <= codes:
        action, team = "Hold withdrawals and verify the account owner's identity (possible account takeover)", "Fraud"
        why = (f"{int(r.impossible_travel_count_30d)} impossible-travel events and a new device used from "
               f"outside Ontario.")
    elif "STRUCTURING" in codes:
        action, team = ("Review deposits for structuring under the $10,000 threshold; assess whether a suspicious "
                        "transaction report is warranted"), "AML"
        why = (f"{int(r.split_threshold_events_30d)} split-deposit episode(s) and "
               f"{int(r.near_threshold_deposits_30d)} deposit(s) just under $10,000 in 30 days.")
    elif {"LINKED_PLAYERS", "CASH_IN_CASH_OUT"} <= codes:
        action, team = "Review the linked accounts as one case; hold withdrawals to shared payment methods", "AML"
        why = (f"{int(r.network_cluster_size)} accounts share identifiers and money is cycled through with "
               f"only {r.turnover_to_deposit_ratio:.0%} of deposits bet.")
    elif {"INCOME_MISMATCH", "CASH_IN_CASH_OUT"} <= codes:
        action, team = "Request source of funds and review for layering", "AML"
        why = (f"Deposits are {r.deposit_income_ratio:.1f}x monthly income and most of the money is withdrawn "
               f"without being bet.")
    elif top["code"] == "INCOME_MISMATCH":
        action, team = "Request source of funds", "AML"
        why = f"Deposits are {r.deposit_income_ratio:.1f}x the monthly income estimate for band {r.income_band}."
    elif top["code"] == "LINKED_PLAYERS":
        action, team = "Review the linked accounts together as one case", "AML"
        why = f"{int(r.network_cluster_size)} accounts share devices, payment methods or an address."
    elif top["code"] == "LARGE_TRANSACTION_24H":
        action, team = "Confirm the 24-hour large transaction is reported and verify the source of funds", "AML"
        why = f"Largest 24-hour deposit total: {money(r.max_deposits_24h_30d)}."
    elif top["code"] == "CASH_IN_CASH_OUT":
        action, team = "Review funds flow for layering", "AML"
        why = f"Only {r.turnover_to_deposit_ratio:.0%} of deposits were bet before withdrawal."
    elif top["anomaly_type"] == "location_anomaly":
        action, team = "Verify the account owner and device", "Fraud"
        why = f"{int(r.out_of_province_txns_30d)} transactions from outside Ontario in 30 days."
    elif len(sg_codes) >= 2 and "LOSS_CHASING" in sg_codes:
        action, team = "Safer Gambling outreach: check in and offer deposit and loss limits", "Safer Gambling"
        why = (f"Losses are {r.loss_change_ratio:.1f}x and deposits {r.deposit_change_ratio:.1f}x the player's "
               f"own 90-day baseline.")
    elif top["anomaly_type"] == "behaviour_change" or top["team"] == "Safer Gambling":
        action, team = "Safer Gambling check-in", "Safer Gambling"
        why = f"{top['title']}: {top['detail']}"
    elif top["code"] in ("PEER_STAKE", "PEER_DEPOSITS"):
        action, team = "Review play against the declared profile; request source of funds if unexplained", "AML"
        z = r.z_avg_stake_30d if top["code"] == "PEER_STAKE" else r.z_deposits_30d
        why = f"{top['title']} (z = {z:.1f}) for peer group {r.peer_group}."
    else:
        action, team = "Manual review: unusual overall pattern with no single dominant rule", "AML"
        why = top["detail"]
    return {"action": action, "team": team, "rationale": why}


# --- Main ---------------------------------------------------------------------------

def run() -> tuple[pd.DataFrame, list[dict]]:
    meta = load_metadata()
    f = pd.read_parquet(FEATURES / "player_features.parquet")
    stats = pd.read_parquet(FEATURES / "peer_stats.parquet").set_index(["peer_group", "feature"])
    f = f.join(isolation_forest(f))
    ml_path = FEATURES / "ml_scores.parquet"
    if ml_path.exists():
        f = f.merge(pd.read_parquet(ml_path), on="player_id", how="left")
    else:
        print("note: data/features/ml_scores.parquet missing; run train_model.py for the AI model reason")
        f["ml_probability"], f["ml_drivers"] = np.nan, "[]"

    def peer_median(group: str, feat: str):
        return float(stats.loc[(group, feat), "median"])

    rows, alerts = [], []
    for r in f.itertuples(index=False):
        reasons = build_reasons(r, peer_median)
        score = min(100, sum(x["points"] for x in reasons))
        band = band_for(score)
        top = next((x for x in reasons if x["team"]), reasons[0]) if reasons else None
        rec = recommend(reasons, r) if reasons else None
        team = rec["team"] if rec else ""
        types = list(dict.fromkeys(x["anomaly_type"] for x in reasons))
        if_points = sum(x["points"] for x in reasons if x["code"] == "ISOLATION_FOREST")
        ml_points = sum(x["points"] for x in reasons if x["code"] == "ML_MODEL")
        ml_prob = None if pd.isna(r.ml_probability) else round(float(r.ml_probability), 4)
        rows.append({
            "player_id": r.player_id, "score": score, "band": band, "team": team,
            "top_reason_code": top["code"] if top else "",
            "reason_codes": "|".join(x["code"] for x in reasons),
            "anomaly_types": "|".join(types),
            "if_percentile": round(float(r.if_percentile), 4), "if_points": if_points,
            "ml_probability": ml_prob, "ml_points": ml_points,
            "alert": score >= ALERT_MIN_SCORE,
        })
        if score < ALERT_MIN_SCORE:
            continue
        alerts.append({
            "alert_id": f"ALR-{r.player_id[1:]}",
            "player_id": r.player_id,
            "score": score,
            "band": band,
            "team": team,
            "status": "New",
            "anomaly_types": types,
            "anomaly_type_labels": [TYPE_LABEL[t] for t in types],
            "top_reason": {"code": top["code"], "title": top["title"]},
            "reasons": reasons,
            "points_total": sum(x["points"] for x in reasons),
            "recommended_action": rec,
            "profile": {"age_band": r.age_band, "occupation": r.occupation, "income_band": r.income_band,
                        "home_region": r.home_region, "signup_date": r.signup_date},
            "peer_group": r.peer_group,
            "peer_group_level": r.peer_group_level,
            "peer_group_size": int(r.peer_group_size),
            "last_activity": None if pd.isna(r.last_activity) else pd.Timestamp(r.last_activity).strftime("%Y-%m-%d %H:%M"),
            "window": {"current_days": 30, "baseline_days": 90, "end_date": meta["end_date"]},
            "ml": None if ml_prob is None else {
                "probability": ml_prob, "drivers": json.loads(r.ml_drivers or "[]"),
                "model": "Gradient boosting + SHAP", "scoring": "out-of-fold"},
            "synthetic": True,
        })
    scores = pd.DataFrame(rows).sort_values(["score", "player_id"], ascending=[False, True])
    alerts.sort(key=lambda a: (-a["score"], a["player_id"]))
    return scores, alerts


def main():
    scores, alerts = run()
    SCORES.mkdir(parents=True, exist_ok=True)
    scores.to_csv(SCORES / "risk_scores.csv", index=False, lineterminator="\n")
    (SCORES / "alerts.json").write_text(json.dumps(alerts, indent=1) + "\n", encoding="utf-8")
    assert all(a["reasons"] and all(x["evidence"] for x in a["reasons"]) for a in alerts), "alert without evidence"
    assert scores.score.between(0, 100).all()
    print(f"alerts={len(alerts)} of {len(scores)} players; bands: {scores.band.value_counts().to_dict()}")
    print("alerts by team:", pd.Series([a['team'] for a in alerts]).value_counts().to_dict())


if __name__ == "__main__":
    main()
