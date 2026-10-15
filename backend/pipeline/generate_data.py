"""Step 1: synthetic sports-betting players and transactions with injected risky behaviour.

Seeded and reproducible: running twice with the same CONFIG produces identical files.
Nothing in the output is real. Player IDs, devices, payment methods and addresses are
random tokens; occupations come from a fixed list mapped to plausible income bands.

Outputs (data/synthetic/):
    players.csv              player_id, age_band, occupation, income_band, home_region, signup_date
    transactions.csv         txn_id, player_id, timestamp, type, amount_cad, sport, market, odds,
                             channel, device_id, ip_region, payment_method_id, event_id, selection
    linked_identifiers.csv   player_id, identifier_type, identifier_value
    scenario_labels.csv      player_id, scenario, start_date, end_date  (ground truth)

Usage:
    python backend/pipeline/generate_data.py [--players N] [--seed S]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    AGE_BANDS,
    FOREIGN_REGIONS,
    HOME_REGIONS,
    INCOME_BANDS,
    SYNTHETIC_DIR,
)

# --------------------------------------------------------------------------------------
# Config (open item #5 in HANDOFF.md: tune here)
# --------------------------------------------------------------------------------------
CONFIG = {
    "seed": 42,
    "n_players": 5000,
    "end_date": "2026-09-30",  # last day of activity (inclusive)
    "days": 180,
    # players per injected scenario (>= 20 each per WORKFLOW "done when")
    "n_income_mismatch": 40,
    "n_peer_deviation": 40,
    "n_location_anomaly": 40,
    "n_behaviour_change": 40,
    "n_rings": 8,
    "ring_size": 5,
    # benign noise that should mostly NOT be flagged (keeps the false-positive story honest)
    "share_travellers": 0.05,  # normal players who take a legit trip out of province
    "share_households": 0.03,  # pairs of normal players sharing an address (and sometimes a device)
    "share_high_rollers": 0.01,  # wealthy players with big but income-consistent stakes
}

OCCUPATIONS = {
    # occupation: allowed income bands (weights)
    "Student": {"<20k": 0.75, "20-40k": 0.25},
    "Retail associate": {"<20k": 0.3, "20-40k": 0.7},
    "Server / hospitality": {"<20k": 0.35, "20-40k": 0.65},
    "Warehouse worker": {"20-40k": 0.6, "40-60k": 0.4},
    "Retired": {"<20k": 0.2, "20-40k": 0.45, "40-60k": 0.25, "60-100k": 0.1},
    "Unemployed": {"<20k": 1.0},
    "Administrative assistant": {"40-60k": 0.8, "20-40k": 0.2},
    "Skilled trades": {"40-60k": 0.4, "60-100k": 0.6},
    "Truck driver": {"40-60k": 0.6, "60-100k": 0.4},
    "Nurse": {"60-100k": 0.85, "100-150k": 0.15},
    "Teacher": {"60-100k": 0.8, "100-150k": 0.2},
    "Police / firefighter": {"60-100k": 0.5, "100-150k": 0.5},
    "Software developer": {"60-100k": 0.35, "100-150k": 0.5, "150k+": 0.15},
    "Accountant": {"60-100k": 0.5, "100-150k": 0.4, "150k+": 0.1},
    "Engineer": {"60-100k": 0.3, "100-150k": 0.55, "150k+": 0.15},
    "Sales manager": {"60-100k": 0.4, "100-150k": 0.4, "150k+": 0.2},
    "Small business owner": {"40-60k": 0.2, "60-100k": 0.35, "100-150k": 0.3, "150k+": 0.15},
    "Lawyer": {"100-150k": 0.4, "150k+": 0.6},
    "Physician": {"150k+": 1.0},
    "Executive": {"150k+": 1.0},
}
OCCUPATION_WEIGHTS = {
    "Student": 0.08, "Retail associate": 0.07, "Server / hospitality": 0.05, "Warehouse worker": 0.06,
    "Retired": 0.07, "Unemployed": 0.02, "Administrative assistant": 0.07, "Skilled trades": 0.09,
    "Truck driver": 0.05, "Nurse": 0.06, "Teacher": 0.06, "Police / firefighter": 0.03,
    "Software developer": 0.06, "Accountant": 0.04, "Engineer": 0.05, "Sales manager": 0.05,
    "Small business owner": 0.05, "Lawyer": 0.02, "Physician": 0.01, "Executive": 0.01,
}
AGE_WEIGHTS = {"18-24": 0.14, "25-34": 0.27, "35-44": 0.23, "45-54": 0.17, "55-64": 0.12, "65+": 0.07}
REGION_WEIGHTS = {"Toronto/GTA": 0.45, "Eastern Ontario": 0.15, "Central Ontario": 0.15,
                  "Southwestern Ontario": 0.15, "Northern Ontario": 0.10}

SPORTS = {  # sport: (weight, markets)
    "NFL": (0.22, ["moneyline", "spread", "total", "player_prop", "parlay"]),
    "NHL": (0.20, ["moneyline", "puck_line", "total", "player_prop", "parlay"]),
    "NBA": (0.16, ["moneyline", "spread", "total", "player_prop", "parlay"]),
    "MLB": (0.12, ["moneyline", "run_line", "total", "parlay"]),
    "Soccer": (0.12, ["1x2", "total", "both_teams_score", "parlay"]),
    "Tennis": (0.06, ["moneyline", "set_handicap"]),
    "CFL": (0.05, ["moneyline", "spread", "total"]),
    "MMA": (0.04, ["moneyline", "method_of_victory"]),
    "Golf": (0.03, ["outright", "top_10"]),
}
OPPOSITE = {"home": "away", "away": "home", "over": "under", "under": "over"}

# Hour-of-day weights for a normal player (evening-heavy, little late-night play)
NORMAL_HOURS = np.array([1.2, 0.7, 0.4, 0.2, 0.1, 0.1, 0.3, 0.8, 1.2, 1.5, 1.8, 2.2,
                         3.0, 3.0, 3.0, 3.3, 4.0, 5.5, 7.5, 9.0, 9.5, 8.5, 6.0, 3.0])
NORMAL_HOURS = NORMAL_HOURS / NORMAL_HOURS.sum()
NIGHT_HOURS = [0, 1, 2, 3, 4, 5]


@dataclass
class Behaviour:
    """Parameters that drive one player's simulated activity over a time window."""
    sessions_per_week: float
    bets_per_session: float
    stake_mean: float
    deposit_size: float
    night_share: float = 0.04
    withdraw_prob: float = 0.25  # chance to cash out at session end when ahead
    bet_fraction: float = 1.0  # share of balance actually put into bets (AML: low)
    chase_prob: float = 0.0  # chance of re-depositing straight after losses
    channels: tuple = ("web", "app", "retail")
    channel_p: tuple = (0.35, 0.55, 0.10)
    devices: list = field(default_factory=list)
    payment_methods: list = field(default_factory=list)
    withdraw_pm: list | None = None  # payment methods used for withdrawals (default = same)
    regions: list = field(default_factory=list)  # ip regions
    region_p: list = field(default_factory=list)


class TxnWriter:
    """Collects transaction rows per player so a scenario can rewrite one player's tail cheaply."""

    def __init__(self):
        self.by_player: dict[str, list[tuple]] = {}

    def raw(self, row: tuple):
        self.by_player.setdefault(row[0], []).append(row)

    def truncate(self, pid, since: datetime | None = None):
        rows = self.by_player.get(pid, [])
        self.by_player[pid] = [] if since is None else [r for r in rows if r[1] < since]

    def all_rows(self):
        for rows in self.by_player.values():
            yield from rows

    def add(self, pid, ts, ttype, amount, b: Behaviour, ctx, sport="", market="", odds=np.nan,
            event_id="", selection=""):
        self.raw((pid, ts, ttype, round(float(amount), 2), sport, market,
                          (round(float(odds), 2) if odds == odds else np.nan),
                          ctx["channel"], ctx["device"], ctx["region"], ctx["pm"], event_id, selection))


def rng_choice(rng, items, p=None):
    return items[rng.choice(len(items), p=p)]


def pick_bet(rng):
    sports = list(SPORTS)
    sp = rng_choice(rng, sports, [SPORTS[s][0] for s in sports])
    market = rng_choice(rng, SPORTS[sp][1])
    if market == "parlay":
        odds = float(np.clip(rng.lognormal(np.log(6.0), 0.6), 2.5, 60))
    elif market in ("outright", "method_of_victory", "top_10"):
        odds = float(np.clip(rng.lognormal(np.log(5.0), 0.7), 1.5, 80))
    else:
        odds = float(np.clip(rng.lognormal(np.log(1.95), 0.25), 1.10, 6.0))
    return sp, market, odds


def event_for(rng, sport, day: datetime):
    return f"{sport[:3].upper()}-{day:%Y%m%d}-{rng.integers(1, 16):02d}"


def simulate(rng, pid, b: Behaviour, t0: datetime, t1: datetime, out: TxnWriter, balance=0.0,
             forced_sessions: list | None = None) -> float:
    """Simulate sessions between t0 and t1. Returns the closing account balance."""
    days = max((t1 - t0).days, 1)
    n_sessions = rng.poisson(b.sessions_per_week * days / 7.0)
    if forced_sessions is None:
        offsets = np.sort(rng.uniform(0, days, n_sessions))
        starts = []
        for off in offsets:
            day = t0 + timedelta(days=int(off))
            if rng.random() < b.night_share:
                hour = int(rng.choice(NIGHT_HOURS))
            else:
                hour = int(rng.choice(24, p=NORMAL_HOURS))
                if hour in NIGHT_HOURS:  # keep night share controlled by b.night_share
                    hour = 22
            starts.append(day.replace(hour=hour, minute=int(rng.integers(0, 60)), second=int(rng.integers(0, 60))))
    else:
        starts = forced_sessions

    for start in starts:
        ctx = {
            "channel": rng_choice(rng, list(b.channels), list(b.channel_p)),
            "device": rng_choice(rng, b.devices),
            "region": rng_choice(rng, b.regions, b.region_p),
            "pm": rng_choice(rng, b.payment_methods),
        }
        if ctx["channel"] == "retail":
            ctx["device"] = "RETAIL-TERMINAL"
        ts = start
        n_bets = 1 + rng.poisson(max(b.bets_per_session - 1, 0))
        if balance < b.stake_mean * 1.5:
            dep = max(20.0, round(b.deposit_size * rng.lognormal(0, 0.35), -1))
            out.add(pid, ts, "deposit", dep, b, ctx)
            balance += dep
        for _ in range(n_bets):
            stake = round(min(balance * b.bet_fraction, b.stake_mean * rng.lognormal(0, 0.5)), 2)
            if stake < 1:
                if rng.random() < b.chase_prob + 0.3:
                    ts += timedelta(minutes=int(rng.integers(1, 6)))
                    dep = max(20.0, round(b.deposit_size * rng.lognormal(0, 0.35), -1))
                    out.add(pid, ts, "deposit", dep, b, ctx)
                    balance += dep
                    stake = round(min(balance * b.bet_fraction, b.stake_mean * rng.lognormal(0, 0.5)), 2)
                else:
                    break
            sp, market, odds = pick_bet(rng)
            ts += timedelta(minutes=int(rng.integers(1, 12)))
            ev = event_for(rng, sp, ts)
            sel = rng_choice(rng, ["home", "away", "over", "under"])
            out.add(pid, ts, "bet", stake, b, ctx, sp, market, odds, ev, sel)
            balance -= stake
            if rng.random() < 0.93 / odds:  # ~7% margin
                payout = round(stake * odds, 2)
                out.add(pid, ts + timedelta(hours=int(rng.integers(1, 4))), "payout", payout, b, ctx, sp, market, odds, ev, sel)
                balance += payout
            elif rng.random() < b.chase_prob:
                ts += timedelta(minutes=int(rng.integers(1, 6)))
                dep = max(20.0, round(b.deposit_size * rng.lognormal(0.2, 0.35), -1))
                out.add(pid, ts, "deposit", dep, b, ctx)
                balance += dep
        if balance > b.deposit_size * 1.5 and rng.random() < b.withdraw_prob:
            amt = round(balance * rng.uniform(0.6, 1.0), 2)
            wctx = dict(ctx)
            if b.withdraw_pm:
                wctx["pm"] = rng_choice(rng, b.withdraw_pm)
            out.add(pid, ts + timedelta(hours=4), "withdrawal", amt, b, wctx)
            balance -= amt
    return balance


def tok(rng, prefix, n=8):
    return f"{prefix}-{''.join(rng.choice(list('0123456789ABCDEFGHJKLMNPQRSTUVWXYZ'), n))}"


def make_players(rng, n, end: datetime):
    occ_names = list(OCCUPATION_WEIGHTS)
    occ_p = np.array([OCCUPATION_WEIGHTS[o] for o in occ_names])
    occ_p /= occ_p.sum()
    rows = []
    for i in range(n):
        age = rng_choice(rng, list(AGE_WEIGHTS), list(AGE_WEIGHTS.values()))
        occ = rng_choice(rng, occ_names, occ_p)
        if age == "18-24" and occ in ("Retired", "Physician", "Lawyer", "Executive"):
            occ = "Student"
        if age == "65+" and occ == "Student":
            occ = "Retired"
        bands = OCCUPATIONS[occ]
        inc = rng_choice(rng, list(bands), list(bands.values()))
        region = rng_choice(rng, list(REGION_WEIGHTS), list(REGION_WEIGHTS.values()))
        signup = end - timedelta(days=int(rng.integers(200, 365 * 6)))
        rows.append({"player_id": f"P{i + 1:05d}", "age_band": age, "occupation": occ,
                     "income_band": inc, "home_region": region, "signup_date": signup.date().isoformat()})
    return pd.DataFrame(rows)


def normal_behaviour(rng, p, devices, pms) -> Behaviour:
    monthly_income = INCOME_BANDS[p["income_band"]] / 12
    budget = monthly_income * float(np.clip(rng.lognormal(np.log(0.012), 0.6), 0.002, 0.06))
    budget = max(budget, 25)
    spw = float(np.clip(rng.lognormal(np.log(1.4), 0.6), 0.25, 8))
    bps = float(1 + rng.poisson(1.5))
    stake = max(2.0, budget * 2.0 / (spw * 4.3 * bps))
    dep = max(20.0, budget / max(spw * 4.3 * 0.45, 1))
    young = p["age_band"] in ("18-24", "25-34")
    old = p["age_band"] in ("55-64", "65+")
    channel_p = (0.25, 0.70, 0.05) if young else ((0.45, 0.25, 0.30) if old else (0.35, 0.55, 0.10))
    return Behaviour(sessions_per_week=spw, bets_per_session=bps, stake_mean=stake, deposit_size=dep,
                     night_share=float(np.clip(rng.normal(0.035, 0.02), 0, 0.10)),
                     channel_p=channel_p, devices=devices, payment_methods=pms,
                     regions=[p["home_region"]], region_p=[1.0])


def neighbouring(region):
    return [r for r in HOME_REGIONS if r != region]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--players", type=int, default=CONFIG["n_players"])
    ap.add_argument("--seed", type=int, default=CONFIG["seed"])
    ap.add_argument("--out", type=Path, default=SYNTHETIC_DIR)
    args = ap.parse_args(argv)

    cfg = dict(CONFIG, n_players=args.players, seed=args.seed)
    rng = np.random.default_rng(cfg["seed"])
    end = datetime.fromisoformat(cfg["end_date"]) + timedelta(days=1)  # exclusive
    start = end - timedelta(days=cfg["days"])

    players = make_players(rng, cfg["n_players"], end)
    pids = players["player_id"].tolist()

    # ---- assign scenarios to disjoint player sets -----------------------------------
    order = list(rng.permutation(len(pids)))
    def take(k):
        return [pids[order.pop()] for _ in range(k)]

    ring_members = take(cfg["n_rings"] * cfg["ring_size"])
    scen_players = {
        "income_mismatch": take(cfg["n_income_mismatch"]),
        "peer_deviation": take(cfg["n_peer_deviation"]),
        "location_anomaly": take(cfg["n_location_anomaly"]),
        "behaviour_change": take(cfg["n_behaviour_change"]),
    }
    n_trav = int(cfg["share_travellers"] * len(pids))
    travellers = set(take(n_trav))
    high_rollers = set(take(int(cfg["share_high_rollers"] * len(pids))))
    households = take(2 * int(cfg["share_households"] * len(pids) / 2))

    p_idx = players.set_index("player_id")
    # Scenario players need profiles that make the scenario meaningful
    for pid in scen_players["income_mismatch"]:
        occ = rng_choice(rng, ["Student", "Retail associate", "Server / hospitality", "Unemployed", "Retired"])
        p_idx.loc[pid, "occupation"] = occ
        p_idx.loc[pid, "income_band"] = "<20k" if occ in ("Student", "Unemployed") else "20-40k"
        if occ == "Retired":
            p_idx.loc[pid, "age_band"] = "65+"
        elif occ == "Student":
            p_idx.loc[pid, "age_band"] = "18-24"
    for pid in list(high_rollers):
        occ = rng_choice(rng, ["Physician", "Executive", "Lawyer"])
        p_idx.loc[pid, "occupation"] = occ
        p_idx.loc[pid, "income_band"] = "150k+"
        if p_idx.loc[pid, "age_band"] == "18-24":
            p_idx.loc[pid, "age_band"] = "35-44"
    for pid in scen_players["peer_deviation"]:
        if p_idx.loc[pid, "income_band"] in ("<20k", "20-40k"):
            p_idx.loc[pid, "income_band"] = "60-100k"
            p_idx.loc[pid, "occupation"] = rng_choice(rng, ["Nurse", "Teacher", "Skilled trades", "Accountant"])
    players = p_idx.reset_index()
    p_idx = players.set_index("player_id")

    # ---- identifiers -----------------------------------------------------------------
    ident = {pid: {"devices": [tok(rng, "DEV")], "pms": [tok(rng, "PM")], "address": tok(rng, "ADDR", 10)}
             for pid in pids}
    for pid in pids:
        if rng.random() < 0.35:
            ident[pid]["devices"].append(tok(rng, "DEV"))
        if rng.random() < 0.25:
            ident[pid]["pms"].append(tok(rng, "PM"))
    for a, b in zip(households[0::2], households[1::2]):  # benign shared address / family tablet
        ident[b]["address"] = ident[a]["address"]
        if rng.random() < 0.5:
            ident[b]["devices"].append(ident[a]["devices"][0])
    rings = [ring_members[i:i + cfg["ring_size"]] for i in range(0, len(ring_members), cfg["ring_size"])]
    for ring in rings:
        shared_dev, shared_pm, shared_addr = tok(rng, "DEV"), tok(rng, "PM"), tok(rng, "ADDR", 10)
        for j, pid in enumerate(ring):
            ident[pid]["devices"].append(shared_dev)
            if j % 2 == 0:
                ident[pid]["pms"].append(shared_pm)
            if j < 3:
                ident[pid]["address"] = shared_addr

    out = TxnWriter()
    labels = []
    cur_start = end - timedelta(days=30)

    base: dict[str, Behaviour] = {}
    for pid in pids:
        p = p_idx.loc[pid]
        b = normal_behaviour(rng, p, ident[pid]["devices"], ident[pid]["pms"])
        base[pid] = b
        if pid in high_rollers:
            b = replace(b, stake_mean=b.stake_mean * 6, deposit_size=b.deposit_size * 6)
        if pid in travellers:  # a 5-12 day legitimate trip, reached by plausible travel time
            trip_start = start + timedelta(days=int(rng.integers(10, cfg["days"] - 15)))
            trip_end = trip_start + timedelta(days=int(rng.integers(5, 12)))
            dest = rng_choice(rng, ["US - Florida", "US - New York", "Quebec", "British Columbia"])
            bal = simulate(rng, pid, b, start, trip_start, out)
            bal = simulate(rng, pid, replace(b, regions=[dest], region_p=[1.0]), trip_start + timedelta(days=1), trip_end, out, bal)
            simulate(rng, pid, b, trip_end + timedelta(days=1), end, out, bal)
        else:
            simulate(rng, pid, b, start, end, out)

    for pid in scen_players["income_mismatch"]:
        p = p_idx.loc[pid]
        whole_period = rng.random() < 0.5
        s0 = start if whole_period else end - timedelta(days=int(rng.integers(25, 45)))
        monthly_income = INCOME_BANDS[p["income_band"]] / 12
        cash_cycle = rng.random() < 0.5  # AML-style: money in, little betting, money out
        b = base[pid]
        mult = float(rng.uniform(1.0, 4.0))  # monthly deposits as a multiple of monthly income
        spw = float(rng.uniform(2.0, 4.0))
        bad = replace(b, sessions_per_week=spw, deposit_size=monthly_income * mult / (spw * 4.3 * 0.7),
                      stake_mean=monthly_income * mult / (spw * 4.3 * (2.5 if cash_cycle else 1.2)),
                      bet_fraction=0.35 if cash_cycle else 1.0, withdraw_prob=0.8 if cash_cycle else 0.3)
        out.truncate(pid, s0)
        simulate(rng, pid, bad, s0, end, out)
        labels.append((pid, "income_mismatch", s0.date(), (end - timedelta(days=1)).date()))

    for pid in scen_players["peer_deviation"]:
        p = p_idx.loc[pid]
        b = base[pid]
        k = float(rng.uniform(12, 25))
        bps = b.bets_per_session + 2
        bad = replace(b, stake_mean=b.stake_mean * k, deposit_size=b.stake_mean * k * bps * 1.2,
                      bets_per_session=bps, sessions_per_week=max(b.sessions_per_week, 2.0))
        out.truncate(pid)
        simulate(rng, pid, bad, start, end, out)
        labels.append((pid, "peer_deviation", start.date(), (end - timedelta(days=1)).date()))

    for pid in scen_players["location_anomaly"]:
        p = p_idx.loc[pid]
        b = replace(base[pid], sessions_per_week=max(base[pid].sessions_per_week, 1.5))
        s0 = end - timedelta(days=int(rng.integers(12, 26)))
        out.truncate(pid, s0)
        new_dev, new_pm = tok(rng, "DEV"), tok(rng, "PM")
        foreign = list(rng.choice(list(FOREIGN_REGIONS), 2, replace=False))
        # account takeover: owner keeps playing at home, someone else plays from abroad on a new device
        bal = simulate(rng, pid, b, s0, end, out)
        intruder = replace(b, devices=[new_dev], regions=foreign + [p["home_region"]], region_p=[0.45, 0.35, 0.20],
                           channels=("web", "app"), channel_p=(0.6, 0.4), sessions_per_week=float(rng.uniform(3, 6)),
                           stake_mean=b.stake_mean * 2.5, deposit_size=b.deposit_size * 2.5, withdraw_pm=[new_pm],
                           withdraw_prob=0.9, night_share=0.25)
        simulate(rng, pid, intruder, s0, end, out, bal)
        labels.append((pid, "location_anomaly", s0.date(), (end - timedelta(days=1)).date()))
        ident[pid]["devices"].append(new_dev)
        ident[pid]["pms"].append(new_pm)

    for pid in scen_players["behaviour_change"]:
        p = p_idx.loc[pid]
        b = replace(base[pid], sessions_per_week=max(base[pid].sessions_per_week, 1.0))
        s0 = end - timedelta(days=int(rng.integers(21, 35)))
        out.truncate(pid, s0)
        k = float(rng.uniform(3, 6))
        bad = replace(b, sessions_per_week=b.sessions_per_week * rng.uniform(2, 3.5), stake_mean=b.stake_mean * k * 0.6,
                      deposit_size=b.deposit_size * k * 0.6, night_share=float(rng.uniform(0.3, 0.55)),
                      chase_prob=float(rng.uniform(0.35, 0.6)), withdraw_prob=0.03)
        simulate(rng, pid, bad, s0, end, out)
        labels.append((pid, "behaviour_change", s0.date(), (end - timedelta(days=1)).date()))

    # ---- linked rings: shared identifiers + opposite bets on the same events ---------
    for ring in rings:
        s0 = end - timedelta(days=int(rng.integers(40, 90)))
        for pid in ring:
            out.truncate(pid, s0)
        n_events = int((end - s0).days / 7 * rng.uniform(2, 3.5))
        for _ in range(n_events):
            day = s0 + timedelta(days=float(rng.uniform(0, (end - s0).days)))
            day = day.replace(hour=int(rng.integers(12, 23)), minute=int(rng.integers(0, 60)), second=0, microsecond=0)
            sp = rng_choice(rng, ["NHL", "NBA", "Soccer", "Tennis"])
            ev = event_for(rng, sp, day)
            side = rng_choice(rng, ["home", "over"])
            pair = list(rng.choice(ring, 2, replace=False))
            stake = round(float(rng.uniform(400, 2500)), -1)
            win = rng.random() < 0.5
            for j, pid in enumerate(pair):
                p = p_idx.loc[pid]
                ctx = {"channel": "app", "device": rng_choice(rng, ident[pid]["devices"]),
                       "region": p["home_region"], "pm": rng_choice(rng, ident[pid]["pms"])}
                ts = day + timedelta(minutes=int(rng.integers(0, 15)))
                sel = side if j == 0 else OPPOSITE[side]
                out.raw((pid, ts, "deposit", stake, "", "", np.nan, ctx["channel"], ctx["device"], ctx["region"], ctx["pm"], "", ""))
                out.raw((pid, ts + timedelta(minutes=2), "bet", stake, sp, "moneyline", 1.91, ctx["channel"], ctx["device"], ctx["region"], ctx["pm"], ev, sel))
                if (j == 0) == win:
                    pay = round(stake * 1.91, 2)
                    out.raw((pid, ts + timedelta(hours=3), "payout", pay, sp, "moneyline", 1.91, ctx["channel"], ctx["device"], ctx["region"], ctx["pm"], ev, sel))
                    out.raw((pid, ts + timedelta(hours=5), "withdrawal", pay, "", "", np.nan, ctx["channel"], ctx["device"], ctx["region"], ctx["pm"], "", ""))
        for pid in ring:
            labels.append((pid, "linked_ring", s0.date(), (end - timedelta(days=1)).date()))

    # ---- assemble -------------------------------------------------------------------
    cols = ["player_id", "timestamp", "type", "amount_cad", "sport", "market", "odds", "channel",
            "device_id", "ip_region", "payment_method_id", "event_id", "selection"]
    txns = pd.DataFrame(list(out.all_rows()), columns=cols)
    txns = txns[(txns["timestamp"] >= start) & (txns["timestamp"] < end)]
    txns = txns.sort_values(["timestamp", "player_id", "type"], kind="mergesort").reset_index(drop=True)
    txns.insert(0, "txn_id", [f"T{i + 1:08d}" for i in range(len(txns))])
    txns["timestamp"] = txns["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # linked identifiers: everything actually observed plus registered address
    li = []
    seen = txns.loc[txns["device_id"] != "RETAIL-TERMINAL", ["player_id", "device_id"]].drop_duplicates()
    li += [(r.player_id, "device", r.device_id) for r in seen.itertuples()]
    seen = txns[["player_id", "payment_method_id"]].drop_duplicates()
    li += [(r.player_id, "payment_method", r.payment_method_id) for r in seen.itertuples()]
    li += [(pid, "address", ident[pid]["address"]) for pid in pids]
    linked = pd.DataFrame(li, columns=["player_id", "identifier_type", "identifier_value"]) \
        .sort_values(["player_id", "identifier_type", "identifier_value"]).reset_index(drop=True)

    lab = pd.DataFrame(labels, columns=["player_id", "scenario", "start_date", "end_date"]) \
        .sort_values(["scenario", "player_id"]).reset_index(drop=True)

    args.out.mkdir(parents=True, exist_ok=True)
    players.to_csv(args.out / "players.csv", index=False)
    txns.to_csv(args.out / "transactions.csv", index=False)
    linked.to_csv(args.out / "linked_identifiers.csv", index=False)
    lab.to_csv(args.out / "scenario_labels.csv", index=False)

    print(f"players: {len(players):,}  transactions: {len(txns):,}  identifiers: {len(linked):,}")
    print(lab["scenario"].value_counts().to_string())
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
