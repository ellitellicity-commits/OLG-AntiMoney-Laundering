"""Step 1 - Synthetic data generator.

Builds a seeded, reproducible population of sports-betting players and their
transactions, then injects known risky behaviour for a labelled subset.

Outputs (data/synthetic/):
    players.csv             player_id, age_band, occupation, income_band, home_region, signup_date,
                            kyc_status, pep, sanctions_screening
    payment_methods.csv     payment_method_id, player_id, method_type, holder_matches_player, first_used
    transactions.csv        txn_id, player_id, timestamp, type, amount_cad, sport, market, odds,
                            channel, device_id, ip_region, payment_method_id
    linked_identifiers.csv  player_id, identifier_type, identifier_value
    scenario_labels.csv     player_id, scenario, start_date, end_date  (ground truth)
    benign_labels.csv       normal players given unusual-but-innocent behaviour (busy month,
                            travel, high roller, household, steady high-value), used to
                            explain false positives in docs/VALIDATION.md (not ground truth)
    metadata.json           seed, date range and counts used by later steps

Injected scenarios: income_mismatch (a third of them with a declared income that is
implausible for their occupation), peer_deviation, location_anomaly, behaviour_change,
structuring (deposits split to stay under the $10,000 reporting threshold),
third_party_funding (deposits from a card in someone else's name, withdrawn to the
player's own account: a "U-turn"), dormant_reactivation (an account silent for months
that suddenly moves large sums), identity_risk (unverified identity or a sanctions
screening hit, with large deposits) and linked_ring (money mules sharing a card and device,
withdrawing to their own accounts).

Benign-but-unusual players also include PEPs, unverified small players, false-positive
sanctions screening matches and household members using a partner's card, so the
compliance checks have realistic false positives.

Everything is synthetic. No real people, accounts or OLG data.

Usage:  python backend/pipeline/generate_data.py [--seed 42] [--players 5000]
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from faker import Faker

from common import AGE_BANDS, HOME_REGIONS, INCOME_BANDS, INCOME_MIDPOINT, REPORTING_THRESHOLD, SYNTH

# --- Config (open item #5: sizes and rates are drafts, adjust here) ----------

CONFIG = {
    "seed": 42,
    "n_players": 5000,
    "days": 180,
    "end_date": "2026-09-30",  # last day of activity (inclusive)
    "scenario_players": {
        "income_mismatch": 40,
        "peer_deviation": 40,
        "location_anomaly": 40,
        "behaviour_change": 40,
        "structuring": 30,
        "third_party_funding": 25,
        "dormant_reactivation": 25,
        "identity_risk": 20,
    },
    "linked_rings": 6,
    "ring_size": (4, 6),
    # Share of the remaining normal players given benign-but-unusual behaviour.
    "benign_rates": {
        "benign_travel": 0.02,
        "benign_surge": 0.03,
        "high_roller": 0.02,
        "household": 0.015,
        # README premise: high earners with a long, steady history of large deposits.
        "steady_high_value": 0.01,
    },
}

DAY = 86_400
HOUR = 3_600

AGE_P = [0.14, 0.27, 0.23, 0.17, 0.12, 0.07]
INCOME_P = [0.06, 0.18, 0.26, 0.21, 0.18, 0.11]
INCOME_P_YOUNG = [0.35, 0.35, 0.18, 0.08, 0.03, 0.01]
HOME_REGION_P = [0.38, 0.14, 0.14, 0.14, 0.10, 0.10]

OCCUPATIONS = {
    "<20k": ["Student", "Part-time retail associate", "Barista", "Server"],
    "20-40k": ["Warehouse associate", "Cashier", "Personal support worker", "Delivery driver", "Line cook"],
    "40-60k": ["Administrative assistant", "Truck driver", "Retail manager", "Bookkeeper", "Machinist"],
    "60-80k": ["Electrician", "Registered practical nurse", "Teacher", "IT support analyst", "Plumber"],
    "80-120k": ["Software developer", "Registered nurse", "Project manager", "Police officer", "Civil engineer"],
    "120k+": ["Physician", "Lawyer", "Senior manager", "Dentist", "Business owner"],
}

SPORTS = ["NFL", "MLB", "Soccer", "NHL", "NBA", "Tennis", "CFL"]
SPORT_P = [0.24, 0.22, 0.18, 0.12, 0.10, 0.08, 0.06]
MARKETS = ["moneyline", "spread", "total", "parlay", "prop"]
MARKET_P = [0.35, 0.20, 0.20, 0.15, 0.10]
CHANNELS = ["app", "web", "retail"]

DAY_HOURS = np.arange(6, 24)
_w = np.array([1, 1, 2, 2, 3, 3, 3, 3, 3, 4, 5, 7, 9, 11, 12, 11, 8, 5], dtype=float)
DAY_HOUR_P = _w / _w.sum()
DAY_HOUR_CUM = np.cumsum(DAY_HOUR_P)
SPORTS_ARR, SPORT_CUM = np.array(SPORTS), np.cumsum(SPORT_P)
MARKETS_ARR, MARKET_CUM = np.array(MARKETS), np.cumsum(MARKET_P)
# Decimal odds range per market, in MARKETS order. Moneyline includes heavy favourites, so
# ordinary players also place some near-certain bets (low-odds betting is a matter of degree).
ODDS_LO = np.array([1.08, 1.83, 1.83, 3.0, 1.6])
ODDS_SPAN = np.array([3.2, 2.05, 2.05, 12.0, 4.5]) - ODDS_LO
PARLAY = MARKETS.index("parlay")

TRAVEL_DESTINATIONS = ["Florida, US", "New York, US", "Quebec"]
TAKEOVER_REGIONS = ["Malta", "Cyprus", "Philippines", "Michigan, US", "Quebec", "Manitoba"]

COLS = ["player_id", "ts", "type", "amount_cad", "sport", "market", "odds",
        "channel", "device_id", "ip_region", "payment_method_id"]


class Ledger:
    """Column-wise row store; much faster than building a DataFrame per row."""

    def __init__(self):
        self.cols = {c: [] for c in COLS}

    def add(self, **row):
        for c in COLS:
            self.cols[c].append(row.get(c, ""))

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.cols)


@dataclass
class Player:
    idx: int
    player_id: str
    age_band: str
    income_band: str
    occupation: str
    home_region: str
    signup_ts: int
    monthly_income: float
    p_active: float
    bets_lam: float
    stake_median: float
    stake_sigma: float
    night_share: float
    channel: str
    devices: list
    pms: list
    deposit_pref: float
    withdraw_trigger: float
    withdraw_prob: float
    address: str
    scenario: str = ""
    benign: str = ""
    kyc_status: str = "verified"
    pep: bool = False
    sanctions: str = "clear"
    inflated_income: bool = False
    pm_holder: dict = field(default_factory=dict)  # payment method -> holder name matches the player
    # Per-day multipliers / overrides, filled in by scenario setup.
    p_mult: np.ndarray = field(default=None)
    stake_mult: np.ndarray = field(default=None)
    extra_lam: np.ndarray = field(default=None)
    night: np.ndarray = field(default=None)
    region: list = field(default=None)
    dep_mult: np.ndarray = field(default=None)


def round_to(x: float, step: float) -> float:
    return float(max(step, np.ceil(x / step) * step))


# --- Population ---------------------------------------------------------------

def make_players(rng: np.random.Generator, fake: Faker, cfg: dict, start_ts: int) -> list[Player]:
    days = cfg["days"]
    players = []
    for i in range(cfg["n_players"]):
        age = AGE_BANDS[rng.choice(6, p=AGE_P)]
        income = INCOME_BANDS[rng.choice(6, p=INCOME_P_YOUNG if age == "18-24" else INCOME_P)]
        occupation = "Retired" if age == "65+" and rng.random() < 0.7 else fake.random_element(OCCUPATIONS[income])
        monthly = INCOME_MIDPOINT[income] / 12
        stake_median = round(monthly * rng.uniform(0.002, 0.008), 2)
        pid = f"P{i + 1:05d}"
        n_dev = 1 + int(rng.random() < 0.35)
        n_pm = 1 + int(rng.random() < 0.25)
        deposit_pref = round_to(stake_median * rng.uniform(2, 5), 10)
        p = Player(
            idx=i, player_id=pid, age_band=age, income_band=income, occupation=occupation,
            home_region=HOME_REGIONS[rng.choice(6, p=HOME_REGION_P)],
            # Every account predates the 180-day window so the 90-day baseline exists.
            signup_ts=int(start_ts - rng.integers(30, 3 * 365) * DAY),
            monthly_income=monthly,
            p_active=float(np.clip(rng.beta(2, 8), 0.03, 0.8)),
            bets_lam=float(rng.uniform(0.3, 2.0)),
            stake_median=stake_median,
            stake_sigma=float(rng.uniform(0.4, 0.8)),
            night_share=float(rng.beta(1.2, 20)),
            channel=CHANNELS[rng.choice(3, p=[0.6, 0.35, 0.05])],
            devices=[f"D{i + 1:05d}-{k}" for k in range(1, n_dev + 1)],
            pms=[f"PM{i + 1:05d}-{k}" for k in range(1, n_pm + 1)],
            deposit_pref=deposit_pref,
            withdraw_trigger=deposit_pref * rng.uniform(1.5, 3),
            withdraw_prob=float(rng.uniform(0.3, 0.8)),
            address=f"ADDR-{rng.integers(16 ** 7, 16 ** 8):08x}",
        )
        p.p_mult = np.ones(days)
        p.stake_mult = np.ones(days)
        p.extra_lam = np.zeros(days)
        p.night = np.full(days, p.night_share)
        p.region = [None] * days
        p.dep_mult = np.ones(days)
        players.append(p)
    return players


def set_income(p: Player, band: str, fake: Faker):
    p.income_band = band
    p.occupation = fake.random_element(OCCUPATIONS[band])
    p.monthly_income = INCOME_MIDPOINT[band] / 12


# --- Normal play ----------------------------------------------------------------

def pick(rng, cum: np.ndarray, n: int) -> np.ndarray:
    """Fast weighted choice of indices (rng.choice with p= is slow for tiny n)."""
    return np.minimum(np.searchsorted(cum, rng.random(n), side="right"), len(cum) - 1)


def make_bets(rng, p: Player, n: int, day_ts: int, stake_median: float, night_share: float,
              low_odds: bool = False):
    """Return (timestamps, stakes, odds, sports, markets, payouts, payout_ts)."""
    night = rng.random(n) < night_share
    hours = np.where(night, rng.integers(0, 6, n), DAY_HOURS[pick(rng, DAY_HOUR_CUM, n)])
    ts = np.sort(day_ts + hours * HOUR + rng.integers(0, HOUR, n))
    if low_odds:
        mk = np.zeros(n, dtype=int)
        odds = rng.uniform(1.05, 1.30, n)
    else:
        mk = pick(rng, MARKET_CUM, n)
        odds = ODDS_LO[mk] + ODDS_SPAN[mk] * rng.random(n)
    odds = np.round(odds, 2)
    stakes = stake_median * rng.lognormal(0, p.stake_sigma, n)
    stakes = np.where(mk == PARLAY, stakes * 0.5, stakes)
    stakes = np.maximum(1.0, np.round(stakes, 2))
    sports = SPORTS_ARR[pick(rng, SPORT_CUM, n)]
    wins = rng.random(n) < 0.95 / odds
    payouts = np.where(wins, np.round(stakes * odds, 2), 0.0)
    payout_ts = ts + rng.integers(int(1.5 * HOUR), 5 * HOUR, n)
    return ts, stakes, odds, sports, MARKETS_ARR[mk], payouts, payout_ts


def day_context(rng, p: Player, d: int):
    channel = p.channel if rng.random() < 0.85 else CHANNELS[rng.choice(2)]
    device = "" if channel == "retail" else (p.devices[0] if rng.random() < 0.8 else p.devices[-1])
    region = p.region[d] or (p.home_region if rng.random() < 0.97 else HOME_REGIONS[rng.choice(6)])
    if channel == "retail":
        region = p.region[d] or p.home_region
    return channel, device, region


def simulate_normal(rng, p: Player, ledger: Ledger, start_ts: int, days: int) -> dict[int, list[int]]:
    """Balance-driven play: deposit when short, bet, settle, sometimes withdraw.

    Returns {day: [bet timestamps]} so other scenarios can anchor to the owner's activity.
    """
    activity: dict[int, list[int]] = {}
    p_day = np.clip(p.p_active * p.p_mult, 0, 0.92)
    active_days = np.flatnonzero(rng.random(days) < p_day)
    balance = 0.0
    for d in active_days:
        day_ts = start_ts + int(d) * DAY
        channel, device, region = day_context(rng, p, d)
        n = 1 + rng.poisson(p.bets_lam + p.extra_lam[d])
        ts, stakes, odds, sports, markets, payouts, pts = make_bets(
            rng, p, n, day_ts, p.stake_median * p.stake_mult[d], p.night[d])
        need = float(stakes.sum())
        pm = p.pms[0] if rng.random() < 0.85 else p.pms[-1]
        if balance < need:
            amount = round_to(max(need - balance, p.deposit_pref * p.dep_mult[d]), 10)
            ledger.add(player_id=p.player_id, ts=int(ts[0] - rng.integers(60, 600)), type="deposit",
                       amount_cad=amount, channel=channel, device_id=device, ip_region=region,
                       payment_method_id=pm)
            balance += amount
        for k in range(n):
            common = dict(player_id=p.player_id, sport=sports[k], market=markets[k], odds=odds[k],
                          channel=channel, device_id=device, ip_region=region)
            ledger.add(ts=int(ts[k]), type="bet", amount_cad=float(stakes[k]), **common)
            if payouts[k] > 0:
                ledger.add(ts=int(pts[k]), type="payout", amount_cad=float(payouts[k]), **common)
        balance += float(payouts.sum()) - need
        if balance > p.withdraw_trigger and rng.random() < p.withdraw_prob:
            amount = round(balance * rng.uniform(0.6, 1.0), 2)
            ledger.add(player_id=p.player_id, ts=int(pts.max() + rng.integers(HOUR, 20 * HOUR)),
                       type="withdrawal", amount_cad=amount, channel=channel, device_id=device,
                       ip_region=region, payment_method_id=pm)
            balance -= amount
        activity[int(d)] = [int(t) for t in ts]
    return activity


# --- Scenario event generators ------------------------------------------------------

def cash_cycle(rng, p: Player, ledger: Ledger, ts: int, deposit: float, bet_share: float,
               withdraw_share: float, pm: str, device: str, region: str, channel: str = "web",
               withdraw_pm: str | None = None, max_wait_days: int = 4):
    """Deposit, a few low-odds bets, then withdraw most of it a few days later.

    withdraw_pm sends the money out to a different payment method than it came in on.
    """
    ledger.add(player_id=p.player_id, ts=ts, type="deposit", amount_cad=deposit, channel=channel,
               device_id=device, ip_region=region, payment_method_id=pm)
    n = int(rng.integers(1, 4))
    stakes = np.round(deposit * bet_share * rng.dirichlet(np.ones(n)), 2)
    t = ts
    for s in stakes:
        t += int(rng.integers(10 * 60, 3 * HOUR))
        odds = round(float(rng.uniform(1.05, 1.30)), 2)
        common = dict(player_id=p.player_id, sport=SPORTS[rng.choice(7, p=SPORT_P)], market="moneyline",
                      odds=odds, channel=channel, device_id=device, ip_region=region)
        ledger.add(ts=t, type="bet", amount_cad=float(max(s, 1.0)), **common)
        if rng.random() < 0.95 / odds:
            ledger.add(ts=t + int(rng.integers(2 * HOUR, 5 * HOUR)), type="payout",
                       amount_cad=round(float(s) * odds, 2), **common)
    if withdraw_share > 0:
        ledger.add(player_id=p.player_id, ts=t + int(rng.integers(6 * HOUR, max_wait_days * DAY)),
                   type="withdrawal", amount_cad=round(deposit * withdraw_share, 2), channel=channel,
                   device_id=device, ip_region=region, payment_method_id=withdraw_pm or pm)


def inject_income_mismatch(rng, p: Player, ledger: Ledger, start_ts: int, s: int, days: int):
    cash_out = p.idx % 2 == 0  # half cycle money in and out, half lose it betting
    d = s
    while d < days:
        ts = start_ts + d * DAY + int(rng.integers(10 * HOUR, 23 * HOUR))
        # Inflated declarers deposit "only" up to ~2x the declared income, so the income check alone
        # misses them; the occupation shows the declared income is implausible.
        deposit = round_to(p.monthly_income * (rng.uniform(0.25, 0.5) if p.inflated_income else rng.uniform(0.6, 1.8)), 50)
        if cash_out:
            cash_cycle(rng, p, ledger, ts, deposit, rng.uniform(0.15, 0.35), rng.uniform(0.6, 0.9),
                       p.pms[0], p.devices[0], p.home_region, p.channel if p.channel != "retail" else "app")
        else:
            ledger.add(player_id=p.player_id, ts=ts, type="deposit", amount_cad=deposit, channel="app",
                       device_id=p.devices[0], ip_region=p.home_region, payment_method_id=p.pms[0])
            n = int(rng.integers(3, 7))
            bts, stakes, odds, sports, markets, payouts, pts = make_bets(
                rng, p, n, start_ts + d * DAY, deposit * rng.uniform(0.5, 1.0) / n, p.night_share)
            for k in range(n):
                common = dict(player_id=p.player_id, sport=sports[k], market=markets[k], odds=odds[k],
                              channel="app", device_id=p.devices[0], ip_region=p.home_region)
                ledger.add(ts=int(max(bts[k], ts + 60)), type="bet", amount_cad=float(stakes[k]), **common)
                if payouts[k] > 0:
                    ledger.add(ts=int(max(pts[k], ts + 2 * HOUR)), type="payout",
                               amount_cad=float(payouts[k]), **common)
        d += int(rng.integers(3, 9))


def inject_takeover(rng, p: Player, ledger: Ledger, start_ts: int, s: int, days: int,
                    activity: dict[int, list[int]]):
    """Someone else uses the account from a new device in another jurisdiction."""
    region = TAKEOVER_REGIONS[rng.choice(len(TAKEOVER_REGIONS))]
    device, pm = f"DX{p.idx + 1:05d}", f"PMX{p.idx + 1:05d}"
    p.pm_holder[pm] = False  # the fraudster's card is not in the account holder's name
    owner_days = [d for d in sorted(activity) if d >= s]
    other_days = [d for d in range(s, days) if d not in activity]
    n_sessions = int(rng.integers(3, 7))
    chosen = owner_days[:2]
    pool = [d for d in owner_days[2:] + other_days]
    if pool:
        extra = rng.choice(pool, size=min(len(pool), max(0, n_sessions - len(chosen))), replace=False)
        chosen += [int(x) for x in extra]
    for d in sorted(chosen):
        if d in activity:  # anchor near the owner's own bet -> impossible travel
            anchor = int(rng.choice(activity[d])) + int(rng.integers(-45 * 60, 45 * 60))
        else:
            anchor = start_ts + d * DAY + int(rng.integers(12 * HOUR, 23 * HOUR))
        deposit = round_to(rng.uniform(200, 1500), 50)
        ledger.add(player_id=p.player_id, ts=anchor, type="deposit", amount_cad=deposit, channel="web",
                   device_id=device, ip_region=region, payment_method_id=pm)
        n = int(rng.integers(2, 6))
        bts, stakes, odds, sports, markets, payouts, pts = make_bets(rng, p, n, 0, deposit / n, 0)
        offsets = np.sort(rng.integers(5 * 60, 2 * HOUR, n))
        won = 0.0
        for k in range(n):
            common = dict(player_id=p.player_id, sport=sports[k], market=markets[k], odds=odds[k],
                          channel="web", device_id=device, ip_region=region)
            ledger.add(ts=anchor + int(offsets[k]), type="bet", amount_cad=float(stakes[k]), **common)
            if payouts[k] > 0:
                ledger.add(ts=anchor + int(offsets[k]) + int(rng.integers(2 * HOUR, 5 * HOUR)),
                           type="payout", amount_cad=float(payouts[k]), **common)
                won += float(payouts[k])
        if won > 0 and rng.random() < 0.7:
            ledger.add(player_id=p.player_id, ts=anchor + 6 * HOUR + int(rng.integers(0, 6 * HOUR)),
                       type="withdrawal", amount_cad=round(won * rng.uniform(0.8, 1.0), 2), channel="web",
                       device_id=device, ip_region=region, payment_method_id=pm)
    return device, pm


def inject_structuring(rng, p: Player, ledger: Ledger, start_ts: int, s: int, days: int):
    """Move large sums in deposits that each stay under the $10,000 reporting threshold.

    Each episode is either two or three deposits just under $10,000 a few hours apart, or
    four to six smaller deposits inside one day that add up past it. Little is bet and
    most of the money is withdrawn again (layering).
    """
    channel = p.channel if p.channel != "retail" else "app"
    d = s
    while d < days:
        t = start_ts + d * DAY + int(rng.integers(8 * HOUR, 13 * HOUR))
        if rng.random() < 0.5:
            amounts = [round_to(rng.uniform(8_500, 9_900), 50) for _ in range(int(rng.integers(2, 4)))]
            gaps = rng.integers(2 * HOUR, 9 * HOUR, len(amounts))
        else:
            n = int(rng.integers(4, 7))
            amounts = [round_to(a, 10) for a in rng.uniform(11_000, 18_000) * rng.dirichlet(np.full(n, 4.0))]
            gaps = rng.integers(30 * 60, 3 * HOUR, n)
        for amount, gap in zip(amounts, gaps):
            cash_cycle(rng, p, ledger, t, float(min(amount, REPORTING_THRESHOLD - 10)), rng.uniform(0.1, 0.3),
                       rng.uniform(0.7, 0.9), p.pms[0], p.devices[0], p.home_region, channel)
            t += int(gap)
        d += int(rng.integers(6, 14))


def inject_ring_flows(rng, p: Player, ledger: Ledger, start_ts: int, s: int, days: int, ring: dict):
    d = s + int(rng.integers(0, 4))
    while d < days:
        ts = start_ts + d * DAY + int(rng.integers(9 * HOUR, 23 * HOUR))
        device = ring["device"] if rng.random() < 0.7 else p.devices[0]
        # Mules fund the shared card's deposits and cash out to their own accounts (U-turn).
        cash_cycle(rng, p, ledger, ts, round_to(rng.uniform(500, 3000), 100), rng.uniform(0.2, 0.4),
                   rng.uniform(0.75, 0.95), ring["pm"], device, p.home_region, withdraw_pm=p.pms[0])
        d += int(rng.integers(4, 10))


def inject_third_party(rng, p: Player, ledger: Ledger, start_ts: int, s: int, days: int):
    """Deposits from a card in someone else's name, withdrawn to the player's own account."""
    pm = f"PMT{p.idx + 1:05d}"
    p.pm_holder[pm] = False
    channel = p.channel if p.channel != "retail" else "app"
    d = s
    while d < days:
        ts = start_ts + d * DAY + int(rng.integers(9 * HOUR, 22 * HOUR))
        cash_cycle(rng, p, ledger, ts, round_to(rng.uniform(800, 3000), 50), rng.uniform(0.2, 0.4),
                   rng.uniform(0.7, 0.9), pm, p.devices[0], p.home_region, channel, withdraw_pm=p.pms[0],
                   max_wait_days=3)
        d += int(rng.integers(3, 8))


def inject_dormant(rng, p: Player, ledger: Ledger, start_ts: int, s: int, days: int):
    """A long-silent account suddenly moves money: large deposits, little betting, fast cash-outs."""
    channel = p.channel if p.channel != "retail" else "app"
    d = s
    while d < days:
        ts = start_ts + d * DAY + int(rng.integers(9 * HOUR, 22 * HOUR))
        deposit = round_to(max(1500.0, p.monthly_income * rng.uniform(0.6, 1.4)), 100)
        cash_cycle(rng, p, ledger, ts, deposit, rng.uniform(0.15, 0.35), rng.uniform(0.6, 0.9), p.pms[0],
                   p.devices[0], p.home_region, channel, max_wait_days=3)
        d += int(rng.integers(4, 9))


def inject_identity_risk(rng, p: Player, ledger: Ledger, start_ts: int, s: int, days: int):
    """Large deposits on an account whose identity is not verified (or that hit sanctions screening)."""
    channel = p.channel if p.channel != "retail" else "app"
    d = s
    while d < days:
        ts = start_ts + d * DAY + int(rng.integers(9 * HOUR, 22 * HOUR))
        cash_cycle(rng, p, ledger, ts, round_to(rng.uniform(1500, 4000), 100), rng.uniform(0.2, 0.5),
                   rng.uniform(0.5, 0.85), p.pms[0], p.devices[0], p.home_region, channel)
        d += int(rng.integers(4, 9))


# --- Main -----------------------------------------------------------------------

def generate(cfg: dict) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(cfg["seed"])
    Faker.seed(cfg["seed"])
    fake = Faker("en_CA")

    days = cfg["days"]
    end_day = pd.Timestamp(cfg["end_date"])
    start_day = end_day - pd.Timedelta(days=days - 1)
    start_ts = int(start_day.timestamp())
    end_ts = int((end_day + pd.Timedelta(days=1)).timestamp())  # exclusive

    players = make_players(rng, fake, cfg, start_ts)
    kyc = rng.choice(["verified", "pending", "expired"], size=len(players), p=[0.965, 0.025, 0.010])
    pep = rng.random(len(players)) < 0.004
    screen_fp = rng.random(len(players)) < 0.002  # name-match false positives, as real screening produces
    for p, k, is_pep, fp in zip(players, kyc, pep, screen_fp):
        p.kyc_status, p.pep, p.sanctions = str(k), bool(is_pep), "potential match" if fp else "clear"
    order = rng.permutation(len(players))
    cursor = 0

    def take(n: int) -> list[Player]:
        nonlocal cursor
        chosen = [players[i] for i in order[cursor:cursor + n]]
        cursor += n
        return chosen

    labels, benign = [], []
    scenario_start: dict[int, int] = {}

    def label(p: Player, scenario: str, s: int, rows: list):
        rows.append({"player_id": p.player_id, "scenario": scenario,
                     "start_date": (start_day + pd.Timedelta(days=s)).date().isoformat(),
                     "end_date": end_day.date().isoformat()})

    # Injected scenarios ---------------------------------------------------------
    for p in take(cfg["scenario_players"]["income_mismatch"]):
        set_income(p, INCOME_BANDS[rng.choice(3)], fake)
        if p.idx % 3 == 0:
            # Declares a high income that the occupation cannot support (keeps a low-income job title).
            job = p.occupation if p.occupation != "Retired" else fake.random_element(OCCUPATIONS["<20k"])
            set_income(p, INCOME_BANDS[4 + rng.choice(2)], fake)
            p.occupation, p.inflated_income = job, True
        p.scenario, s = "income_mismatch", int(rng.integers(30, days - 60))
        scenario_start[p.idx] = s
        label(p, p.scenario, s, labels)

    for p in take(cfg["scenario_players"]["peer_deviation"]):
        set_income(p, INCOME_BANDS[3 + rng.choice(3)], fake)
        # 8-15x the *typical* stake for the band, i.e. far above the peer median.
        p.stake_median = round(p.monthly_income * 0.005, 2)
        p.stake_mult[:] = rng.uniform(8, 15)
        p.p_mult[:] = 0.8
        p.p_active = max(p.p_active, 0.12)
        p.deposit_pref = round_to(p.stake_median * p.stake_mult[0] * 3, 10)
        p.scenario = "peer_deviation"
        label(p, p.scenario, 0, labels)

    for p in take(cfg["scenario_players"]["location_anomaly"]):
        p.scenario, s = "location_anomaly", days - int(rng.integers(8, 26))
        p.p_active = max(p.p_active, 0.15)
        scenario_start[p.idx] = s
        label(p, p.scenario, s, labels)

    for p in take(cfg["scenario_players"]["behaviour_change"]):
        p.scenario, s = "behaviour_change", days - int(rng.integers(18, 36))
        p.p_mult[s:] = (min(0.85, p.p_active * 3 + 0.2)) / p.p_active
        p.stake_mult[s:] = rng.uniform(2.5, 4.0)
        p.extra_lam[s:] = rng.uniform(1.0, 2.5)
        p.night[s:] = rng.uniform(0.35, 0.6)
        p.dep_mult[s:] = 3.0
        label(p, p.scenario, s, labels)

    for p in take(cfg["scenario_players"]["structuring"]):
        set_income(p, INCOME_BANDS[2 + rng.choice(4)], fake)
        p.scenario, s = "structuring", days - int(rng.integers(25, 50))
        scenario_start[p.idx] = s
        label(p, p.scenario, s, labels)

    for p in take(cfg["scenario_players"]["third_party_funding"]):
        p.scenario, s = "third_party_funding", days - int(rng.integers(25, 45))
        scenario_start[p.idx] = s
        label(p, p.scenario, s, labels)

    for p in take(cfg["scenario_players"]["dormant_reactivation"]):
        s = days - int(rng.integers(15, 26))
        p.p_mult[30:s] = 0.0  # active in the first month, then silent until the reactivation
        p.p_mult[s:] = 0.0    # after reactivation only the injected money movement
        p.scenario = "dormant_reactivation"
        scenario_start[p.idx] = s
        label(p, p.scenario, s, labels)

    for i, p in enumerate(take(cfg["scenario_players"]["identity_risk"])):
        p.kyc_status = ["pending", "expired"][i % 2]
        if i % 4 == 0:
            p.kyc_status, p.sanctions = "verified", "potential match"
        p.scenario, s = "identity_risk", days - int(rng.integers(25, 45))
        scenario_start[p.idx] = s
        label(p, p.scenario, s, labels)

    rings = []
    for r in range(cfg["linked_rings"]):
        lo, hi = cfg["ring_size"]
        members = take(int(rng.integers(lo, hi + 1)))
        ring = {"device": f"D-R{r + 1}", "pm": f"PM-R{r + 1}", "address": f"ADDR-R{r + 1:02d}",
                "region": HOME_REGIONS[rng.choice(6, p=HOME_REGION_P)], "members": members}
        s = int(rng.integers(days - 100, days - 40))
        for p in members:
            p.scenario, p.home_region, p.address = "linked_ring", ring["region"], ring["address"]
            p.pm_holder[ring["pm"]] = False
            scenario_start[p.idx] = s
            label(p, p.scenario, s, labels)
        rings.append(ring)

    # Benign-but-unusual normal players ----------------------------------------------
    remaining = len(players) - cursor
    rates = cfg["benign_rates"]
    for p in take(int(remaining * rates["benign_travel"])):
        s, length = days - int(rng.integers(5, 55)), int(rng.integers(3, 8))
        dest = TRAVEL_DESTINATIONS[rng.choice(3)]
        for d in range(s, min(days, s + length)):
            p.region[d] = dest
        p.p_mult[s:s + length] = max(1.0, 0.5 / p.p_active)
        p.benign = "benign_travel"
        label(p, p.benign, s, benign)
    for p in take(int(remaining * rates["benign_surge"])):
        s = days - 30
        p.p_mult[s:] = min(1.8, 0.9 / p.p_active)
        p.stake_mult[s:] = rng.uniform(1.5, 2.0)
        p.benign = "benign_surge"
        label(p, p.benign, s, benign)
    for p in take(int(remaining * rates["high_roller"])):
        set_income(p, INCOME_BANDS[4 + rng.choice(2)], fake)
        p.stake_median = round(p.monthly_income * rng.uniform(0.002, 0.008), 2)
        p.stake_mult[:] = rng.uniform(3, 5)
        p.benign = "high_roller"
        label(p, p.benign, 0, benign)
    for p in take(int(remaining * rates["steady_high_value"])):
        set_income(p, INCOME_BANDS[4 + rng.choice(2)], fake)
        p.stake_median = round(p.monthly_income * rng.uniform(0.015, 0.03), 2)
        p.p_active = float(rng.uniform(0.5, 0.8))
        p.bets_lam = float(rng.uniform(1.5, 3.0))
        p.deposit_pref = round_to(p.stake_median * rng.uniform(4, 8), 50)
        p.withdraw_trigger = p.deposit_pref * 2
        p.benign = "steady_high_value"
        label(p, p.benign, 0, benign)
    household = take(2 * int(remaining * rates["household"] / 2))
    for a, b in zip(household[::2], household[1::2]):
        b.address, b.home_region = a.address, a.home_region
        if rng.random() < 0.5:
            b.devices = [b.devices[0], a.devices[0]]
        if rng.random() < 0.3:  # sometimes deposits with the partner's card (benign third-party payment)
            b.pms = [b.pms[0], a.pms[0]]
            b.pm_holder[a.pms[0]] = False
        for p in (a, b):
            p.benign = "household"
            label(p, p.benign, 0, benign)

    for p in players:  # compliance attributes on ordinary players are benign until behaviour says otherwise
        if p.scenario:
            continue
        if p.pep:
            label(p, "pep", 0, benign)
        if p.sanctions != "clear":
            label(p, "screening_false_positive", 0, benign)
        if p.kyc_status != "verified":
            label(p, "unverified_identity", 0, benign)

    # Simulate ------------------------------------------------------------------------
    ledger = Ledger()
    extra_ids = {}
    for p in players:
        activity = simulate_normal(rng, p, ledger, start_ts, days)
        if p.scenario == "income_mismatch":
            inject_income_mismatch(rng, p, ledger, start_ts, scenario_start[p.idx], days)
        elif p.scenario == "location_anomaly":
            extra_ids[p.player_id] = inject_takeover(rng, p, ledger, start_ts, scenario_start[p.idx], days, activity)
        elif p.scenario == "structuring":
            inject_structuring(rng, p, ledger, start_ts, scenario_start[p.idx], days)
        elif p.scenario == "third_party_funding":
            inject_third_party(rng, p, ledger, start_ts, scenario_start[p.idx], days)
        elif p.scenario == "dormant_reactivation":
            inject_dormant(rng, p, ledger, start_ts, scenario_start[p.idx], days)
        elif p.scenario == "identity_risk":
            inject_identity_risk(rng, p, ledger, start_ts, scenario_start[p.idx], days)
    for ring in rings:
        for p in ring["members"]:
            inject_ring_flows(rng, p, ledger, start_ts, scenario_start[p.idx], days, ring)

    # Assemble ------------------------------------------------------------------------
    tx = ledger.frame()
    tx = tx[(tx["ts"] >= start_ts) & (tx["ts"] < end_ts)]
    tx = tx.sort_values(["ts", "player_id"], kind="stable").reset_index(drop=True)
    tx.insert(0, "txn_id", [f"T{i + 1:07d}" for i in range(len(tx))])
    tx.insert(2, "timestamp", pd.to_datetime(tx.pop("ts"), unit="s").dt.strftime("%Y-%m-%d %H:%M:%S"))
    tx["amount_cad"] = tx["amount_cad"].astype(float).round(2)

    players_df = pd.DataFrame([{
        "player_id": p.player_id, "age_band": p.age_band, "occupation": p.occupation,
        "income_band": p.income_band, "home_region": p.home_region,
        "signup_date": pd.to_datetime(p.signup_ts, unit="s").date().isoformat(),
        "kyc_status": p.kyc_status, "pep": p.pep, "sanctions_screening": p.sanctions,
    } for p in players])

    # Payment methods actually used, with the holder check a payments provider would return.
    by_id = {p.player_id: p for p in players}
    used_pm = (tx.loc[tx.payment_method_id != "", ["player_id", "payment_method_id", "timestamp"]]
               .groupby(["payment_method_id", "player_id"], as_index=False).timestamp.min()
               .sort_values(["payment_method_id", "player_id"]).reset_index(drop=True))
    pm_ids = used_pm.payment_method_id.unique()
    pm_type = dict(zip(pm_ids, rng.choice(["debit card", "credit card", "bank transfer", "e-wallet"],
                                          size=len(pm_ids), p=[0.45, 0.2, 0.25, 0.1])))
    payment_methods = pd.DataFrame({
        "payment_method_id": used_pm.payment_method_id,
        "player_id": used_pm.player_id,
        "method_type": used_pm.payment_method_id.map(pm_type),
        "holder_matches_player": [by_id[pid].pm_holder.get(pm, True)
                                  for pid, pm in zip(used_pm.player_id, used_pm.payment_method_id)],
        "first_used": used_pm.timestamp.str.slice(0, 10),
    })

    # Linked identifiers: every device / payment method actually used, plus address.
    used = pd.concat([
        tx.loc[tx.device_id != "", ["player_id", "device_id"]].drop_duplicates()
          .rename(columns={"device_id": "identifier_value"}).assign(identifier_type="device"),
        tx.loc[tx.payment_method_id != "", ["player_id", "payment_method_id"]].drop_duplicates()
          .rename(columns={"payment_method_id": "identifier_value"}).assign(identifier_type="payment_method"),
        pd.DataFrame({"player_id": [p.player_id for p in players],
                      "identifier_value": [p.address for p in players]}).assign(identifier_type="address"),
    ])
    linked = (used[["player_id", "identifier_type", "identifier_value"]]
              .sort_values(["player_id", "identifier_type", "identifier_value"]).reset_index(drop=True))

    labels_df = pd.DataFrame(labels).sort_values("player_id").reset_index(drop=True)
    benign_df = (pd.DataFrame(benign).rename(columns={"scenario": "pattern"})
                 .sort_values(["player_id", "pattern"]).reset_index(drop=True))

    meta = {
        "seed": cfg["seed"], "n_players": len(players_df), "n_transactions": len(tx),
        "start_date": start_day.date().isoformat(), "end_date": end_day.date().isoformat(),
        "scenario_counts": labels_df.scenario.value_counts().sort_index().to_dict(),
        "benign_counts": benign_df.pattern.value_counts().sort_index().to_dict(),
        "note": "All data is synthetic. No real players, transactions or OLG data.",
    }
    return {"players": players_df, "transactions": tx, "linked_identifiers": linked,
            "payment_methods": payment_methods,
            "scenario_labels": labels_df, "benign_labels": benign_df, "metadata": meta}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=CONFIG["seed"])
    ap.add_argument("--players", type=int, default=CONFIG["n_players"])
    args = ap.parse_args()
    cfg = CONFIG | {"seed": args.seed, "n_players": args.players}

    out = generate(cfg)
    SYNTH.mkdir(parents=True, exist_ok=True)
    for name in ["players", "transactions", "linked_identifiers", "payment_methods", "scenario_labels",
                 "benign_labels"]:
        out[name].to_csv(SYNTH / f"{name}.csv", index=False, lineterminator="\n")
    (SYNTH / "metadata.json").write_text(json.dumps(out["metadata"], indent=2) + "\n", encoding="utf-8")
    m = out["metadata"]
    print(f"players={m['n_players']} transactions={m['n_transactions']} "
          f"window={m['start_date']}..{m['end_date']}")
    print("scenarios:", m["scenario_counts"])
    print("benign:", m["benign_counts"])


if __name__ == "__main__":
    main()
