"""Shared paths and constants for the pipeline scripts and the API.

Kept free of relative imports so it works both as `from common import ...`
(when a pipeline script is run directly) and as `backend.pipeline.common`.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SYNTH = DATA / "synthetic"
FEATURES = DATA / "features"
SCORES = DATA / "scores"
MODELS = DATA / "models"
DOCS = ROOT / "docs"

# --- Player profile vocabulary -------------------------------------------------

AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
INCOME_BANDS = ["<20k", "20-40k", "40-60k", "60-80k", "80-120k", "120k+"]
# Annual midpoint used for the monthly income estimate (annual / 12).
INCOME_MIDPOINT = {
    "<20k": 15_000, "20-40k": 30_000, "40-60k": 50_000,
    "60-80k": 70_000, "80-120k": 100_000, "120k+": 150_000,
}

HOME_REGIONS = ["Toronto", "Ottawa", "Hamilton-Niagara", "Southwestern ON", "Eastern ON", "Northern ON"]

# Every IP region maps to a jurisdiction. Ontario regions are "ON".
JURISDICTION = {r: "ON" for r in HOME_REGIONS} | {
    "Quebec": "QC", "Manitoba": "MB",
    "New York, US": "US", "Michigan, US": "US", "Florida, US": "US",
    "Malta": "INTL", "Cyprus": "INTL", "Philippines": "INTL",
}

# Minimum plausible hours to travel between two jurisdictions. Two
# transactions closer together than this are "impossible travel".
_TRAVEL_HOURS = {
    frozenset({"ON", "QC"}): 1.5, frozenset({"ON", "US"}): 1.5, frozenset({"ON", "MB"}): 2.5,
    frozenset({"QC", "US"}): 1.5, frozenset({"QC", "MB"}): 3.0, frozenset({"MB", "US"}): 2.5,
}
INTL_TRAVEL_HOURS = 7.0


def min_travel_hours(a: str, b: str) -> float:
    if a == b:
        return 0.0
    if "INTL" in (a, b):
        return INTL_TRAVEL_HOURS
    return _TRAVEL_HOURS[frozenset({a, b})]


# --- Risk bands (DESIGN.md §2; confirmed in step 4, see docs/VALIDATION.md) ---

BANDS = [(90, "Critical"), (70, "High"), (40, "Medium"), (0, "Low")]
ALERT_MIN_SCORE = 40  # players at Medium or above become alerts in the queue


# --- Compliance thresholds ---------------------------------------------------------
# FINTRAC-style indicators: a $10,000+ total within 24 hours is reportable as one large
# transaction (the "24-hour rule"); repeated deposits just under it suggest structuring.
# Indicators only: this tool does not decide reporting obligations.

REPORTING_THRESHOLD = 10_000
NEAR_THRESHOLD = 8_000

# Per-transaction flags written by build_features.py and shown in the activity table.
TXN_FLAGS = {
    "OUTSIDE_ONTARIO": "Outside Ontario",
    "IMPOSSIBLE_TRAVEL": "Impossible travel",
    "NEW_DEVICE": "New device",
    "NEW_PAYMENT_METHOD": "New payment method",
    "LARGE_DEPOSIT": "Large deposit for this player",
    "NEAR_THRESHOLD": "Just under $10,000",
    "THRESHOLD_24H": "$10,000+ within 24 hours",
    "LOW_ODDS_BET": "Low-odds bet",
}

# Human labels for model features (Isolation Forest and the supervised model).
FEATURE_LABEL = {
    "deposits_30d": "30-day deposits", "avg_stake_30d": "average stake", "bets_per_day_30d": "bets per day",
    "net_loss_30d": "30-day net loss", "deposit_income_ratio": "deposits vs income",
    "deposit_change_ratio": "deposits vs own baseline", "stake_change_ratio": "stake vs own baseline",
    "loss_change_ratio": "losses vs own baseline", "night_share_30d": "night betting share",
    "night_share_change": "change in night betting", "withdrawal_to_deposit_ratio": "withdrawals vs deposits",
    "turnover_to_deposit_ratio": "betting turnover vs deposits", "distinct_ip_regions_30d": "distinct locations",
    "share_outside_ontario_30d": "share outside Ontario", "impossible_travel_count_30d": "impossible-travel events",
    "new_devices_30d": "new devices", "new_payment_methods_30d": "new payment methods",
    "shared_identifier_count": "shared identifiers", "z_deposits_30d": "deposits vs peers",
    "z_avg_stake_30d": "average stake vs peers", "z_bets_per_day_30d": "bet frequency vs peers",
    "z_net_loss_30d": "net loss vs peers", "deposit_count_30d": "number of deposits",
    "max_deposit_30d": "largest deposit", "network_cluster_size": "linked-account cluster size",
    "new_devices_outside_ontario_30d": "new devices outside Ontario",
    "threshold_24h_events_30d": "$10,000+ 24-hour totals", "near_threshold_deposits_30d": "deposits just under $10,000",
    "split_threshold_events_30d": "split deposits crossing $10,000", "max_deposits_24h_30d": "largest 24-hour deposit total",
}


def band_for(score: float) -> str:
    for cut, name in BANDS:
        if score >= cut:
            return name
    return "Low"


def symlog(x):
    """Sign-preserving log1p. Spend data is heavy-tailed; z-scores use this scale."""
    x = np.asarray(x, dtype=float)
    return np.sign(x) * np.log1p(np.abs(x))


def load_metadata() -> dict:
    return json.loads((SYNTH / "metadata.json").read_text(encoding="utf-8"))
