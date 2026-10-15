"""Shared paths, reference data and settings for the pipeline and the API.

Anything a teammate may want to tune (windows, thresholds, band cut-offs) lives here or in
the CONFIG block at the top of each step script.
"""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
FEATURES_DIR = DATA_DIR / "features"
SCORES_DIR = DATA_DIR / "scores"

# ---- profile reference data ----------------------------------------------------------
AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

# income band -> annual income estimate (CAD) used for spend-vs-income features
INCOME_BANDS = {
    "<20k": 15_000,
    "20-40k": 30_000,
    "40-60k": 50_000,
    "60-100k": 80_000,
    "100-150k": 125_000,
    "150k+": 200_000,
}

# Ontario home regions with an approximate centre (lat, lon) for travel-speed checks
HOME_REGIONS = {
    "Toronto/GTA": (43.70, -79.42),
    "Eastern Ontario": (45.42, -75.70),
    "Central Ontario": (44.39, -79.69),
    "Southwestern Ontario": (42.98, -81.25),
    "Northern Ontario": (46.49, -80.99),
}
# Regions outside Ontario that can appear as ip_region
FOREIGN_REGIONS = {
    "Quebec": (45.50, -73.57),
    "Manitoba": (49.90, -97.14),
    "British Columbia": (49.28, -123.12),
    "US - New York": (40.71, -74.00),
    "US - Florida": (25.76, -80.19),
    "US - Nevada": (36.17, -115.14),
    "United Kingdom": (51.51, -0.13),
    "Malta": (35.90, 14.51),
    "Cyprus": (35.17, 33.36),
    "Romania": (44.43, 26.10),
}
ALL_REGIONS = {**HOME_REGIONS, **FOREIGN_REGIONS}
OUTSIDE_CANADA = {r for r in FOREIGN_REGIONS if r not in ("Quebec", "Manitoba", "British Columbia")}

# ---- analysis windows ----------------------------------------------------------------
CURRENT_DAYS = 30
BASELINE_DAYS = 90
MAX_TRAVEL_KMH = 900  # faster than this between two transactions = impossible travel

# ---- scoring -------------------------------------------------------------------------
# Open item #8: risk-band cut-offs (draft from DESIGN.md)
BANDS = [(90, "Critical"), (70, "High"), (40, "Medium"), (0, "Low")]
ALERT_MIN_SCORE = 40  # players at or above this score become alerts in the queue

ANOMALY_TYPES = ["income_mismatch", "peer_deviation", "location_anomaly", "behaviour_change", "linked_ring"]


def band_for(score: float) -> str:
    for cut, name in BANDS:
        if score >= cut:
            return name
    return "Low"


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
