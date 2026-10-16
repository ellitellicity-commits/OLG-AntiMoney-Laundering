"""Checks the "done when" criteria from docs/WORKFLOW.md steps 1-4."""
from __future__ import annotations

import filecmp
import json
import subprocess
import sys

import pandas as pd
from conftest import N_PLAYERS, PIPELINE, ROOT, evaluate, generate

from common import band_for


def test_generation_is_deterministic(data_dir, tmp_path):
    generate(tmp_path)
    for name in ["players.csv", "transactions.csv", "linked_identifiers.csv", "scenario_labels.csv"]:
        assert filecmp.cmp(data_dir / "synthetic" / name, tmp_path / "synthetic" / name, shallow=False), name


def test_required_columns_and_scenarios(data_dir):
    players = pd.read_csv(data_dir / "synthetic" / "players.csv")
    txns = pd.read_csv(data_dir / "synthetic" / "transactions.csv", nrows=1000)
    linked = pd.read_csv(data_dir / "synthetic" / "linked_identifiers.csv")
    labels = pd.read_csv(data_dir / "synthetic" / "scenario_labels.csv")
    assert {"player_id", "age_band", "occupation", "income_band", "home_region", "signup_date"} <= set(players.columns)
    assert {"txn_id", "player_id", "timestamp", "type", "amount_cad", "sport", "market", "odds", "channel",
            "device_id", "ip_region", "payment_method_id"} <= set(txns.columns)
    assert set(txns["type"]) <= {"deposit", "withdrawal", "bet", "payout"}
    assert set(txns["channel"]) <= {"web", "app", "retail"}
    assert {"player_id", "identifier_type", "identifier_value"} <= set(linked.columns)
    counts = labels["scenario"].value_counts()
    for scen in ["income_mismatch", "peer_deviation", "location_anomaly", "behaviour_change", "linked_ring"]:
        assert counts.get(scen, 0) >= 20, scen
    assert players["player_id"].is_unique and len(players) == N_PLAYERS


def test_generated_data_passes_the_data_contract_check(data_dir):
    r = subprocess.run([sys.executable, str(PIPELINE / "check_data.py"), "--dir", str(data_dir / "synthetic")],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr


def test_features_one_row_per_player(data_dir):
    f = pd.read_parquet(data_dir / "features" / "player_features.parquet")
    assert len(f) == N_PLAYERS and f["player_id"].is_unique
    for col in ["deposits_30d", "deposit_income_ratio", "peer_group", "behaviour_cluster", "network_cluster_size"]:
        assert f[col].notna().all(), col


def test_injected_players_stand_out(data_dir):
    f = pd.read_parquet(data_dir / "features" / "player_features.parquet")
    labels = pd.read_csv(data_dir / "synthetic" / "scenario_labels.csv")
    f = f.merge(labels[["player_id", "scenario"]], how="left").fillna({"scenario": "normal"})
    med = f.groupby("scenario").median(numeric_only=True)
    assert med.loc["income_mismatch", "deposit_income_ratio"] > 10 * med.loc["normal", "deposit_income_ratio"]
    assert (med.loc["location_anomaly", "share_outside_home_region_30d"] > 0.2
            > med.loc["normal", "share_outside_home_region_30d"])
    assert med.loc["behaviour_change", "deposit_change_ratio"] > 3 * med.loc["normal", "deposit_change_ratio"]
    assert med.loc["linked_ring", "network_cluster_size"] >= 3 > med.loc["normal", "network_cluster_size"]


def test_scores_and_alerts_are_explained(data_dir):
    scores = pd.read_csv(data_dir / "scores" / "risk_scores.csv")
    assert scores["score"].between(0, 99).all()
    assert (scores["band"] == scores["score"].map(band_for)).all()
    alerts = json.loads((data_dir / "scores" / "alerts.json").read_text(encoding="utf-8"))
    assert alerts, "expected some alerts"
    for a in alerts:
        assert a["reasons"], a["alert_id"]
        assert all(r["evidence"] and r["detail"] for r in a["reasons"])
        assert a["recommended_action"]["action"] and a["recommended_action"]["team"] in {"AML", "Fraud", "Safer Gambling"}
        # every point of the score traces back to a reason
        assert a["points_total"] == sum(r["points"] for r in a["reasons"])
        assert a["confidence"]["level"] in {"High", "Medium", "Low"}
    order = [(a["score"], a["points_total"]) for a in alerts]
    assert order == sorted(order, reverse=True)


def test_validation_beats_rules_only(data_dir):
    rep = evaluate(data_dir)
    for r in rep["recall"].values():
        assert 0 <= r["recall_alerted"] <= 1
    p = rep["precision_at_k"]
    assert p["combined"]["p@50"] >= p["legacy_rules_only"]["p@50"]
    assert rep["false_positive_rate"]["combined"] < 0.02
