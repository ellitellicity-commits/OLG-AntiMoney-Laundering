"""Shared paths and constants for the pipeline scripts and the API.

Kept free of relative imports so it works both as `from common import ...`
(when a pipeline script is run directly) and as `backend.pipeline.common`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
# OLG_DATA_DIR points the whole pipeline at another folder (used by cross_seed.py to build
# throwaway test populations without touching the demo data).
DATA = Path(os.environ["OLG_DATA_DIR"]).resolve() if os.environ.get("OLG_DATA_DIR") else ROOT / "data"
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

# Typical annual income range per declared occupation (illustrative figures for synthetic data).
# Used to check the declared income band against the occupation (brief: "spend inconsistent with
# reported occupation or income range"). None = income varies too widely to judge from the title.
OCCUPATION_INCOME = {
    "Student": (0, 25_000), "Part-time retail associate": (10_000, 30_000), "Barista": (15_000, 35_000),
    "Server": (15_000, 40_000), "Warehouse associate": (30_000, 50_000), "Cashier": (20_000, 38_000),
    "Personal support worker": (30_000, 50_000), "Delivery driver": (28_000, 55_000), "Line cook": (25_000, 45_000),
    "Administrative assistant": (40_000, 60_000), "Truck driver": (45_000, 80_000), "Retail manager": (45_000, 80_000),
    "Bookkeeper": (40_000, 65_000), "Machinist": (45_000, 75_000), "Electrician": (55_000, 100_000),
    "Registered practical nurse": (55_000, 80_000), "Teacher": (55_000, 105_000), "IT support analyst": (50_000, 85_000),
    "Plumber": (55_000, 100_000), "Software developer": (75_000, 150_000), "Registered nurse": (75_000, 115_000),
    "Project manager": (75_000, 140_000), "Police officer": (80_000, 125_000), "Civil engineer": (75_000, 130_000),
    "Physician": (200_000, 500_000), "Lawyer": (100_000, 400_000), "Senior manager": (110_000, 300_000),
    "Dentist": (150_000, 400_000), "Business owner": None, "Retired": None,
}
INCOME_BAND_RANGE = {"<20k": (0, 20_000), "20-40k": (20_000, 40_000), "40-60k": (40_000, 60_000),
                     "60-80k": (60_000, 80_000), "80-120k": (80_000, 120_000), "120k+": (120_000, 10**9)}

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
    "THIRD_PARTY_PAYMENT": "Card / account in another name",
    "UTURN_WITHDRAWAL": "Withdrawn to a different method",
    "QUICK_CASH_OUT": "Withdrawn within 72 h of deposit",
}
LOW_ODDS = 1.30  # decimal odds below this are near-certain bets (minimal-risk betting)

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
    "low_odds_share_30d": "share of stakes on near-certain bets", "third_party_deposits_30d": "deposits from third-party methods",
    "uturn_withdrawals_30d": "withdrawals to a different method", "quick_cashouts_30d": "quick cash-outs",
    "dormant_days_before_30d": "days dormant before this month", "occupation_income_ratio": "declared vs occupation income",
    "deposit_occupation_ratio": "deposits vs occupation income", "z_cluster_deposits_30d": "deposits vs behaviour peers",
    "z_cluster_avg_stake_30d": "average stake vs behaviour peers", "kyc_unverified": "identity not verified",
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
