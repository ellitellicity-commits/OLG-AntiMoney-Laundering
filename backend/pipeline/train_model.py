"""Step 2b - Supervised risk model (gradient boosting) with SHAP explanations.

Learns which combinations of player features match the labelled risky scenarios, as a
second opinion next to the hand-written rules. The model is scikit-learn's
HistGradientBoostingClassifier (free, no extra install); SHAP (TreeExplainer) says which
features pushed each player's probability up, so the model's output becomes one more
evidence-backed reason line instead of a black-box number.

Honest scoring: every player's probability and SHAP drivers come from a model that never
saw that player (5-fold out-of-fold predictions). The final model trained on all players
is saved for reuse, but the scores used in detect.py and validate.py are out-of-fold.

Labels: injected scenarios = 1, everyone else = 0. Benign-but-unusual players (high
rollers, travellers, busy months) are negatives, which is exactly what the model should
learn to tell apart from real risk.

Inputs:  data/features/player_features.parquet, data/synthetic/scenario_labels.csv
Outputs: data/features/ml_scores.parquet  player_id, ml_probability, ml_drivers (JSON list)
         data/models/risk_model.joblib    final model + feature list
         data/models/model_card.json      metrics, feature importance, caveats

Usage:  python backend/pipeline/train_model.py
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from common import FEATURE_LABEL, FEATURES, MODELS, SYNTH, load_metadata

SEED = 42
FOLDS = 5
TOP_DRIVERS = 3
MIN_DRIVER_IMPACT = 0.15  # log-odds; smaller pushes are noise, not an explanation

ML_FEATURES = [
    "deposits_30d", "deposit_count_30d", "max_deposit_30d", "avg_stake_30d", "bets_per_day_30d", "net_loss_30d",
    "deposit_income_ratio", "deposit_change_ratio", "stake_change_ratio", "loss_change_ratio",
    "night_share_30d", "night_share_change", "withdrawal_to_deposit_ratio", "turnover_to_deposit_ratio",
    "z_deposits_30d", "z_avg_stake_30d", "z_bets_per_day_30d", "z_net_loss_30d",
    "distinct_ip_regions_30d", "share_outside_ontario_30d", "impossible_travel_count_30d",
    "new_devices_30d", "new_devices_outside_ontario_30d", "new_payment_methods_30d",
    "shared_identifier_count", "network_cluster_size",
    "threshold_24h_events_30d", "split_threshold_events_30d", "near_threshold_deposits_30d", "max_deposits_24h_30d",
]
PARAMS = dict(learning_rate=0.06, max_iter=250, max_leaf_nodes=15, min_samples_leaf=20,
              l2_regularization=1.0, random_state=SEED)


def make_model() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(**PARAMS)


def shap_values(model, x: pd.DataFrame) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sv = shap.TreeExplainer(model).shap_values(x)
    sv = np.asarray(sv[1] if isinstance(sv, list) else sv)
    return sv[..., 1] if sv.ndim == 3 else sv  # (n, features) log-odds contributions to "risky"


def drivers(x: pd.DataFrame, sv: np.ndarray, typical: pd.Series) -> list[str]:
    """Top features pushing the probability up, as JSON per player.

    Only features where the player sits above most players (75th percentile) are kept: a
    tree model can push risk up for an *ordinary* value through interactions, which is
    true to the model but reads as nonsense to an investigator ("risky because deposits
    are low"). Those pushes still count in the probability, they just aren't listed.
    """
    above = (x.to_numpy() > typical.to_numpy()) & (sv >= MIN_DRIVER_IMPACT)
    out = []
    for i in range(len(x)):
        order = [j for j in np.argsort(-sv[i]) if above[i, j]][:TOP_DRIVERS]
        out.append(json.dumps([
            {"feature": ML_FEATURES[j], "label": FEATURE_LABEL.get(ML_FEATURES[j], ML_FEATURES[j]),
             "value": round(float(x.iat[i, j]), 4), "impact": round(float(sv[i, j]), 3)}
            for j in order]))
    return out


def precision_at(prob: pd.Series, y: pd.Series, k: int) -> float:
    return round(float(y[prob.sort_values(ascending=False, kind="stable").index[:k]].mean()), 3)


def train() -> tuple[pd.DataFrame, dict, HistGradientBoostingClassifier]:
    f = pd.read_parquet(FEATURES / "player_features.parquet").set_index("player_id")
    labels = pd.read_csv(SYNTH / "scenario_labels.csv")
    x = f[ML_FEATURES].astype(float)
    y = pd.Series(f.index.isin(labels.player_id).astype(int), index=f.index)

    typical = x.quantile(0.75)
    prob = pd.Series(np.nan, index=f.index)
    drv = pd.Series("", index=f.index, dtype=object)
    sv_all = np.zeros(x.shape)
    for train_idx, test_idx in StratifiedKFold(FOLDS, shuffle=True, random_state=SEED).split(x, y):
        model = make_model().fit(x.iloc[train_idx], y.iloc[train_idx])
        xt = x.iloc[test_idx]
        prob.iloc[test_idx] = model.predict_proba(xt)[:, 1]
        sv = shap_values(model, xt)
        sv_all[test_idx] = sv
        drv.iloc[test_idx] = drivers(xt, sv, typical)

    final = make_model().fit(x, y)
    importance = pd.Series(np.abs(sv_all).mean(axis=0), index=ML_FEATURES).sort_values(ascending=False)
    scen = labels.set_index("player_id").scenario
    recall_by_scenario = {s: round(float((prob[g.index] >= 0.5).mean()), 3) for s, g in scen.groupby(scen)}
    card = {
        "model": "HistGradientBoostingClassifier (scikit-learn)",
        "explainer": "SHAP TreeExplainer (log-odds contributions)",
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_seed": load_metadata()["seed"],
        "players": int(len(y)), "positives": int(y.sum()), "features": ML_FEATURES, "params": PARAMS,
        "evaluation": "5-fold stratified out-of-fold predictions (each player scored by a model that never saw them)",
        "metrics": {
            "roc_auc": round(float(roc_auc_score(y, prob)), 4),
            "average_precision": round(float(average_precision_score(y, prob)), 4),
            "precision_at_50": precision_at(prob, y, 50), "precision_at_100": precision_at(prob, y, 100),
            "recall_at_0.5": round(float((prob[y == 1] >= 0.5).mean()), 3),
            "false_positive_rate_at_0.5": round(float((prob[y == 0] >= 0.5).mean()), 4),
            "recall_at_0.5_by_scenario": recall_by_scenario,
        },
        "global_importance": [{"feature": k, "label": FEATURE_LABEL.get(k, k), "mean_abs_shap": round(float(v), 4)}
                              for k, v in importance.head(12).items()],
        "caveats": [
            "Trained and evaluated on synthetic data whose risky scenarios were designed by the same team; "
            "the metrics show the pipeline works, not real-world performance.",
            "A production model would be trained on investigator-confirmed outcomes (decisions.json) and "
            "monitored for drift; it supports, and never replaces, the rule reasons and investigator judgement.",
        ],
    }
    scores = pd.DataFrame({"ml_probability": prob.round(4), "ml_drivers": drv}).reset_index()
    return scores, card, final


def main():
    scores, card, final = train()
    FEATURES.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(FEATURES / "ml_scores.parquet", index=False)
    joblib.dump({"model": final, "features": ML_FEATURES}, MODELS / "risk_model.joblib")
    (MODELS / "model_card.json").write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    m = card["metrics"]
    print(f"out-of-fold ROC-AUC={m['roc_auc']} AP={m['average_precision']} p@50={m['precision_at_50']} "
          f"recall@0.5={m['recall_at_0.5']} FPR@0.5={m['false_positive_rate_at_0.5']}")
    print("recall@0.5 by scenario:", m["recall_at_0.5_by_scenario"])
    print("top features:", [g["feature"] for g in card["global_importance"][:6]])


if __name__ == "__main__":
    main()
