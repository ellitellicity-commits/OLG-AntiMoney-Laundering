"""Step 2: per-player features (current 30 days vs prior 90-day baseline) and peer-group stats.

Reference date = the day after the last transaction. Windows:
    current  = [ref - 30d, ref)
    baseline = [ref - 120d, ref - 30d)    (monthly figures = baseline total / 3)

Peer group: age_band x income_band x home_region. Groups with fewer than MIN_PEER_GROUP players
fall back to age_band x income_band, then to income_band alone.

Feature list (one row per player in player_features.parquet):
    monthly_income_estimate     midpoint of declared income band / 12
    deposits_30d                total deposits in the current window (CAD)
    deposit_count_30d           number of deposits in the current window
    max_deposit_30d             largest single deposit in the current window
    withdrawals_30d             total withdrawals in the current window
    turnover_30d                total amount staked in the current window
    payouts_30d                 total winnings paid in the current window
    net_loss_30d                turnover - payouts (positive = player lost money)
    bet_count_30d               number of bets in the current window
    avg_stake_30d               mean stake per bet in the current window
    bets_per_day_30d            bet_count_30d / 30
    active_days_30d             distinct days with any transaction
    night_share_30d             share of bets placed 00:00-05:59
    deposit_to_income           deposits_30d / monthly_income_estimate
    withdrawal_to_deposit_30d   withdrawals_30d / deposits_30d
    turnover_to_deposit_30d     turnover_30d / deposits_30d (low = money in and out without betting)
    chase_deposits_30d          deposits made within 15 min of a losing bet
    deposits_baseline_m         baseline deposits per 30 days
    avg_stake_baseline          mean stake in the baseline window
    bets_per_day_baseline       baseline bets per day
    night_share_baseline        baseline share of night bets
    net_loss_baseline_m         baseline net loss per 30 days
    deposit_change_ratio        (deposits_30d + 50) / (deposits_baseline_m + 50)
    stake_change_ratio          (avg_stake_30d + 5) / (avg_stake_baseline + 5)
    activity_change_ratio       (bets_per_day_30d + 0.1) / (bets_per_day_baseline + 0.1)
    night_share_change          night_share_30d - night_share_baseline
    distinct_ip_regions_30d     distinct ip regions in the current window
    share_outside_home_30d      share of transactions outside the player's home region
    share_outside_canada_30d    share of transactions from outside Canada
    impossible_travel_count_30d consecutive transactions implying travel faster than MAX_TRAVEL_KMH
    new_devices_30d             devices first seen in the current window
    new_payment_methods_30d     payment methods first seen in the current window
    withdrawals_to_new_pm_30d   withdrawals paid to a payment method first seen in the current window
    shared_identifier_count     identifiers (device / payment method / address) shared with other players
    linked_players              distinct other players sharing at least one identifier
    opposite_bets_with_linked   bets on the same event as a linked player but on the opposite side
    peer_group                  label of the peer group used
    peer_group_size             players in that peer group
    z_<f>, pct_<f>              robust z-score and percentile within the peer group for PEER_FEATURES

Outputs: data/features/player_features.parquet, data/features/peer_stats.parquet,
         data/features/transactions.parquet (typed copy used by the API)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ALL_REGIONS,
    BASELINE_DAYS,
    CURRENT_DAYS,
    FEATURES_DIR,
    INCOME_BANDS,
    MAX_TRAVEL_KMH,
    OUTSIDE_CANADA,
    SYNTHETIC_DIR,
)

MIN_PEER_GROUP = 30
PEER_FEATURES = ["deposits_30d", "avg_stake_30d", "bets_per_day_30d", "net_loss_30d", "turnover_30d", "max_deposit_30d"]
# monetary / count features are compared on a log scale so a few whales don't hide everyone else
LOG_FEATURES = {"deposits_30d", "avg_stake_30d", "net_loss_30d", "turnover_30d", "max_deposit_30d", "bets_per_day_30d"}


def load_transactions(path: Path = SYNTHETIC_DIR / "transactions.csv") -> pd.DataFrame:
    t = pd.read_csv(path, dtype={"event_id": "string", "selection": "string", "sport": "string", "market": "string"})
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    for c in ["player_id", "type", "channel", "ip_region", "sport", "market", "selection"]:
        t[c] = t[c].astype("category")
    return t


def reference_date(t: pd.DataFrame) -> pd.Timestamp:
    return t["timestamp"].max().normalize() + pd.Timedelta(days=1)


def window_aggregates(t: pd.DataFrame, prefix: str) -> pd.DataFrame:
    g = t.groupby("player_id", observed=True)
    dep = t[t["type"] == "deposit"].groupby("player_id", observed=True)["amount_cad"]
    wd = t[t["type"] == "withdrawal"].groupby("player_id", observed=True)["amount_cad"]
    bets = t[t["type"] == "bet"]
    b = bets.groupby("player_id", observed=True)
    pay = t[t["type"] == "payout"].groupby("player_id", observed=True)["amount_cad"]
    out = pd.DataFrame({
        "deposits": dep.sum(), "deposit_count": dep.size(), "max_deposit": dep.max(),
        "withdrawals": wd.sum(), "turnover": b["amount_cad"].sum(), "bet_count": b.size(),
        "payouts": pay.sum(),
        "night_share": bets.assign(n=bets["timestamp"].dt.hour < 6).groupby("player_id", observed=True)["n"].mean(),
        "active_days": g["timestamp"].apply(lambda s: s.dt.normalize().nunique()),
    })
    out = out.fillna(0)
    out["net_loss"] = out["turnover"] - out["payouts"]
    out["avg_stake"] = np.where(out["bet_count"] > 0, out["turnover"] / out["bet_count"].clip(lower=1), 0)
    return out.add_suffix(prefix)


def chase_deposits(cur: pd.DataFrame) -> pd.Series:
    """Deposits made within 15 minutes after a bet that did not pay out."""
    paid = set(cur.loc[cur["type"] == "payout", ["player_id", "event_id"]].astype(str).agg("|".join, axis=1))
    s = cur[cur["type"].isin(["bet", "deposit"])].sort_values(["player_id", "timestamp"])
    prev_type = s.groupby("player_id", observed=True)["type"].shift()
    prev_ts = s.groupby("player_id", observed=True)["timestamp"].shift()
    prev_key = (s["player_id"].astype(str) + "|" + s.groupby("player_id", observed=True)["event_id"].shift().astype(str))
    lost = ~prev_key.isin(paid)
    m = (s["type"] == "deposit") & (prev_type == "bet") & ((s["timestamp"] - prev_ts) <= pd.Timedelta(minutes=15)) & lost
    return m.groupby(s["player_id"], observed=True).sum()


def location_features(cur: pd.DataFrame, home: pd.Series) -> pd.DataFrame:
    s = cur.sort_values(["player_id", "timestamp"])[["player_id", "timestamp", "ip_region"]].copy()
    s["ip_region"] = s["ip_region"].astype(str)
    lat = s["ip_region"].map(lambda r: ALL_REGIONS.get(r, (np.nan, np.nan))[0])
    lon = s["ip_region"].map(lambda r: ALL_REGIONS.get(r, (np.nan, np.nan))[1])
    grp = s.groupby("player_id", observed=True)
    plat, plon, pts, preg = grp["timestamp"].shift(), None, None, None
    plat = lat.groupby(s["player_id"], observed=True).shift()
    plon = lon.groupby(s["player_id"], observed=True).shift()
    pts = grp["timestamp"].shift()
    preg = grp["ip_region"].shift()
    la1, lo1, la2, lo2 = map(np.radians, (plat, plon, lat, lon))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    km = 2 * 6371 * np.arcsin(np.sqrt(h))
    hours = ((s["timestamp"] - pts).dt.total_seconds() / 3600).clip(lower=1 / 60)
    impossible = (preg.notna()) & (preg != s["ip_region"]) & ((km / hours) > MAX_TRAVEL_KMH)
    s["outside_home"] = s["ip_region"].values != s["player_id"].map(home).astype(str).values
    s["outside_canada"] = s["ip_region"].isin(OUTSIDE_CANADA)
    g = s.groupby("player_id", observed=True)
    return pd.DataFrame({
        "distinct_ip_regions_30d": g["ip_region"].nunique(),
        "share_outside_home_30d": g["outside_home"].mean(),
        "share_outside_canada_30d": g["outside_canada"].mean(),
        "impossible_travel_count_30d": impossible.groupby(s["player_id"], observed=True).sum(),
    })


def new_identifier_features(t: pd.DataFrame, cur_start: pd.Timestamp) -> pd.DataFrame:
    first_dev = t[t["device_id"] != "RETAIL-TERMINAL"].groupby(["player_id", "device_id"], observed=True)["timestamp"].min()
    first_pm = t.groupby(["player_id", "payment_method_id"], observed=True)["timestamp"].min()
    new_dev = (first_dev >= cur_start).groupby(level=0, observed=True).sum()
    new_pm_idx = first_pm[first_pm >= cur_start].index
    new_pm = pd.Series(1, index=new_pm_idx).groupby(level=0).sum() if len(new_pm_idx) else pd.Series(dtype=float)
    w = t[(t["type"] == "withdrawal") & (t["timestamp"] >= cur_start)]
    w_new = w.set_index(["player_id", "payment_method_id"]).index.isin(new_pm_idx)
    wn = pd.Series(w_new, index=w["player_id"].values).groupby(level=0).sum()
    return pd.DataFrame({"new_devices_30d": new_dev, "new_payment_methods_30d": new_pm, "withdrawals_to_new_pm_30d": wn})


def network_features(linked: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    shared = linked.groupby(["identifier_type", "identifier_value"])["player_id"].transform("nunique") > 1
    sl = linked[shared]
    pairs = sl.merge(sl, on=["identifier_type", "identifier_value"])
    pairs = pairs[pairs["player_id_x"] != pairs["player_id_y"]]
    out = pd.DataFrame({
        "shared_identifier_count": sl.groupby("player_id").size(),
        "linked_players": pairs.groupby("player_id_x")["player_id_y"].nunique(),
    })
    # opposite-side bets on the same event between linked players (chip-dumping style)
    link_set = pairs[["player_id_x", "player_id_y"]].drop_duplicates()
    bets = t.loc[(t["type"] == "bet") & t["event_id"].notna(), ["player_id", "event_id", "selection"]].copy()
    bets["player_id"] = bets["player_id"].astype(str)
    bets["selection"] = bets["selection"].astype(str)
    bets = bets[bets["player_id"].isin(set(link_set["player_id_x"]))]
    m = bets.merge(bets, on="event_id")
    m = m[(m["player_id_x"] != m["player_id_y"]) & (m["selection_x"] != m["selection_y"])]
    m = m.merge(link_set, on=["player_id_x", "player_id_y"])
    out["opposite_bets_with_linked"] = m.groupby("player_id_x").size()
    return out


def assign_peer_groups(players: pd.DataFrame) -> pd.Series:
    levels = [["age_band", "income_band", "home_region"], ["age_band", "income_band"], ["income_band"]]
    label = pd.Series(index=players.index, dtype=object)
    for cols in levels:
        key = players[cols].astype(str).agg(" | ".join, axis=1)
        size = key.map(key.value_counts())
        fill = label.isna() & (size >= MIN_PEER_GROUP)
        label[fill] = key[fill]
    label = label.fillna(players["income_band"].astype(str))
    return label


def peer_statistics(f: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, zcols = [], {}
    for feat in PEER_FEATURES:
        x = np.log1p(f[feat].clip(lower=0)) if feat in LOG_FEATURES else f[feat]
        g = f.groupby("peer_group")[feat]
        gl = x.groupby(f["peer_group"])
        med_l, q1_l, q3_l = gl.transform("median"), gl.transform(lambda s: s.quantile(0.25)), gl.transform(lambda s: s.quantile(0.75))
        scale = ((q3_l - q1_l) / 1.349).clip(lower=0.25 if feat in LOG_FEATURES else 0.05)
        zcols[f"z_{feat}"] = ((x - med_l) / scale).round(3)
        zcols[f"pct_{feat}"] = g.rank(pct=True).round(4)
        st = g.agg(n="size", median="median", q1=lambda s: s.quantile(0.25), q3=lambda s: s.quantile(0.75),
                   p90=lambda s: s.quantile(0.9), mean="mean", std="std")
        st["iqr"] = st["q3"] - st["q1"]
        st["feature"] = feat
        rows.append(st.reset_index())
    stats = pd.concat(rows, ignore_index=True)[["peer_group", "feature", "n", "median", "q1", "q3", "iqr", "p90", "mean", "std"]]
    return stats, pd.DataFrame(zcols, index=f.index)


def build(synthetic_dir: Path = SYNTHETIC_DIR, out_dir: Path = FEATURES_DIR) -> pd.DataFrame:
    players = pd.read_csv(synthetic_dir / "players.csv")
    linked = pd.read_csv(synthetic_dir / "linked_identifiers.csv")
    t = load_transactions(synthetic_dir / "transactions.csv")

    ref = reference_date(t)
    cur_start = ref - pd.Timedelta(days=CURRENT_DAYS)
    base_start = cur_start - pd.Timedelta(days=BASELINE_DAYS)
    cur = t[t["timestamp"] >= cur_start]
    base = t[(t["timestamp"] >= base_start) & (t["timestamp"] < cur_start)]

    f = players.set_index("player_id")
    f["monthly_income_estimate"] = f["income_band"].map(INCOME_BANDS) / 12
    f = f.join(window_aggregates(cur, "_30d")).join(window_aggregates(base, "_b"))
    f = f.fillna({c: 0 for c in f.columns if c.endswith(("_30d", "_b"))})
    f["bets_per_day_30d"] = f["bet_count_30d"] / CURRENT_DAYS
    f["deposits_baseline_m"] = f["deposits_b"] * CURRENT_DAYS / BASELINE_DAYS
    f["avg_stake_baseline"] = f["avg_stake_b"]
    f["bets_per_day_baseline"] = f["bet_count_b"] / BASELINE_DAYS
    f["night_share_baseline"] = f["night_share_b"]
    f["net_loss_baseline_m"] = f["net_loss_b"] * CURRENT_DAYS / BASELINE_DAYS
    f = f.drop(columns=[c for c in f.columns if c.endswith("_b")])

    f["deposit_to_income"] = f["deposits_30d"] / f["monthly_income_estimate"]
    f["withdrawal_to_deposit_30d"] = np.where(f["deposits_30d"] > 0, f["withdrawals_30d"] / f["deposits_30d"].clip(lower=1), 0)
    f["turnover_to_deposit_30d"] = np.where(f["deposits_30d"] > 0, f["turnover_30d"] / f["deposits_30d"].clip(lower=1), 0)
    f["chase_deposits_30d"] = chase_deposits(cur)
    f["deposit_change_ratio"] = (f["deposits_30d"] + 50) / (f["deposits_baseline_m"] + 50)
    f["stake_change_ratio"] = (f["avg_stake_30d"] + 5) / (f["avg_stake_baseline"] + 5)
    f["activity_change_ratio"] = (f["bets_per_day_30d"] + 0.1) / (f["bets_per_day_baseline"] + 0.1)
    f["night_share_change"] = f["night_share_30d"] - f["night_share_baseline"]

    f = f.join(location_features(cur, f["home_region"]))
    f = f.join(new_identifier_features(t, cur_start))
    f = f.join(network_features(linked, t))
    num = f.select_dtypes("number").columns
    f[num] = f[num].fillna(0)
    for c in ["deposit_count_30d", "bet_count_30d", "active_days_30d", "distinct_ip_regions_30d", "impossible_travel_count_30d",
              "new_devices_30d", "new_payment_methods_30d", "withdrawals_to_new_pm_30d", "shared_identifier_count",
              "linked_players", "opposite_bets_with_linked", "chase_deposits_30d"]:
        f[c] = f[c].astype(int)

    f["peer_group"] = assign_peer_groups(f)
    f["peer_group_size"] = f["peer_group"].map(f["peer_group"].value_counts()).astype(int)
    stats, z = peer_statistics(f)
    f = f.join(z)
    f["reference_date"] = ref.date().isoformat()
    f = f.round(4).reset_index()

    out_dir.mkdir(parents=True, exist_ok=True)
    f.to_parquet(out_dir / "player_features.parquet", index=False)
    stats.to_parquet(out_dir / "peer_stats.parquet", index=False)
    t.to_parquet(out_dir / "transactions.parquet", index=False)
    return f


def main():
    f = build()
    print(f"features: {len(f):,} players x {f.shape[1]} columns; peer groups: {f['peer_group'].nunique()}")
    print(f"written to {FEATURES_DIR}")


if __name__ == "__main__":
    main()
