"""Checks the "done when" criteria from docs/WORKFLOW.md steps 1-4."""
from __future__ import annotations

import filecmp
import json

import pandas as pd
from conftest import N_PLAYERS, SEED

import generate_data
from common import band_for


def test_generation_is_deterministic(data_dir, tmp_path):
    generate_data.main(["--players", str(N_PLAYERS), "--seed", str(SEED), "--out", str(tmp_path)])
    for name in ["players.csv", "transactions.csv", "linked_identifiers.csv", "scenario_labels.csv"]:
        assert filecmp.cmp(data_dir / "synthetic" / name, tmp_path / name, shallow=False), name


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


def test_features_one_row_per_player_no_nulls(data_dir):
    f = pd.read_parquet(data_dir / "features" / "player_features.parquet")
    assert len(f) == N_PLAYERS and f["player_id"].is_unique
    num = f.select_dtypes("number")
    assert not num.isna().any().any(), num.columns[num.isna().any()].tolist()


def test_injected_players_stand_out(data_dir):
    f = pd.read_parquet(data_dir / "features" / "player_features.parquet")
    labels = pd.read_csv(data_dir / "synthetic" / "scenario_labels.csv")
    f = f.merge(labels[["player_id", "scenario"]], how="left").fillna({"scenario": "normal"})
    med = f.groupby("scenario").median(numeric_only=True)
    assert med.loc["income_mismatch", "deposit_to_income"] > 10 * med.loc["normal", "deposit_to_income"]
    assert med.loc["location_anomaly", "share_outside_home_30d"] > 0.2 > med.loc["normal", "share_outside_home_30d"]
    assert med.loc["behaviour_change", "deposit_change_ratio"] > 3 * med.loc["normal", "deposit_change_ratio"]
    assert med.loc["linked_ring", "opposite_bets_with_linked"] > 0 == med.loc["normal", "opposite_bets_with_linked"]


def test_scores_and_alerts_are_explained(data_dir):
    scores = pd.read_csv(data_dir / "scores" / "risk_scores.csv")
    assert scores["score"].between(0, 100).all()
    assert (scores["band"] == scores["score"].map(band_for)).all()
    alerts = json.loads((data_dir / "scores" / "alerts.json").read_text(encoding="utf-8"))
    assert alerts, "expected some alerts"
    for a in alerts:
        assert a["reasons"], a["alert_id"]
        assert all(r["evidence"] and r["detail"] for r in a["reasons"])
        assert a["recommended_action"]["action"] and a["recommended_action"]["team"] in {"AML", "Fraud", "Safer Gambling"}
        # the score is the capped sum of reason points
        assert a["score"] == min(100, sum(a["points_by_type"].values()))
        assert a["reasons"][0]["anomaly_type"] == a["recommended_action"]["primary_type"]
    assert [a["score"] for a in alerts] == sorted((a["score"] for a in alerts), reverse=True)


def test_validation_beats_rules_only(data_dir):
    rep = json.loads((data_dir / "scores" / "validation_report.json").read_text(encoding="utf-8"))
    for scen, r in rep["recall_by_scenario"].items():
        assert 0 <= r["recall"] <= 1
    assert rep["precision_at_k"]["p@50"]["combined"] >= rep["precision_at_k"]["p@50"]["rules_only"]
    assert rep["overall"]["false_positive_rate"] < 0.02
    assert (data_dir / "docs" / "VALIDATION.md").exists()
