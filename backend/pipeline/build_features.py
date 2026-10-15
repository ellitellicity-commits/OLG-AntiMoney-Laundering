"""Step 2 - Per-player features, own-baseline comparisons and peer-group statistics.

Windows (relative to the dataset end date in metadata.json):
    current  = last 30 days
    baseline = the 90 days before that, expressed per 30 days so the two compare directly

Features (one row per player in data/features/player_features.parquet):
    monthly_income_estimate        income band midpoint / 12
    deposits_30d                   total deposited in the current window ($)
    deposit_count_30d              number of deposits in the current window
    max_deposit_30d                largest single deposit in the current window ($)
    withdrawals_30d                total withdrawn in the current window ($)
    bets_30d                       number of bets in the current window
    turnover_30d                   total staked in the current window ($)
    payouts_30d                    total paid out on winning bets ($)
    net_loss_30d                   turnover - payouts (negative = player is up)
    avg_stake_30d                  turnover / bets
    bets_per_day_30d               bets / 30
    night_share_30d                share of bets placed 00:00-05:59
    deposits_base_30d              baseline deposits per 30 days
    avg_stake_base                 baseline average stake
    bets_per_day_base              baseline bets per day
    net_loss_base_30d              baseline net loss per 30 days
    night_share_base               baseline share of night bets
    deposit_income_ratio           deposits_30d / monthly_income_estimate
    deposit_change_ratio           deposits_30d / max(deposits_base_30d, $50)
    stake_change_ratio             avg_stake_30d / max(avg_stake_base, $5)
    night_share_change             night_share_30d - night_share_base
    loss_change_ratio              net_loss_30d / max(net_loss_base_30d, $50)
    withdrawal_to_deposit_ratio    withdrawals_30d / deposits_30d
    turnover_to_deposit_ratio      turnover_30d / deposits_30d (low = money in and out without real betting)
    distinct_ip_regions_30d        distinct IP regions seen in the current window
    share_outside_home_region_30d  share of transactions not from the home region
    share_outside_ontario_30d      share of transactions from outside Ontario
    out_of_province_txns_30d       count of transactions from outside Ontario
    impossible_travel_count_30d    consecutive transactions too close in time for the distance
    impossible_travel_example      first such pair, as "Toronto 21:04 -> Malta 21:40 (36 min)"
    new_devices_30d                devices first seen in the current window
    new_devices_outside_ontario_30d  new devices that were used from outside Ontario
    new_payment_methods_30d        payment methods first seen in the current window
    shared_identifier_count        devices / payment methods / addresses shared with other players
    linked_player_count            other players sharing at least one identifier
    network_cluster_id             connected component in the shared-identifier graph
    network_cluster_size           players in that component (1 = not linked)
    threshold_24h_events_30d       episodes where deposits within 24 hours reached $10,000 (24-hour rule)
    split_threshold_events_30d     ... of which every deposit was under $10,000 (2+ deposits): possible structuring
    near_threshold_deposits_30d    deposits between $8,000 and $9,999.99
    max_deposits_24h_30d           largest 24-hour deposit total in the current window ($)
    threshold_24h_example          largest such episode, as "2026-09-12: 3 deposits totalling $14,350.00 ..."
    last_activity                  timestamp of the player's latest transaction
    peer_group, peer_group_level, peer_group_size
    z_<metric>                     robust peer z-score on a symlog scale, for PEER_Z_FEATURES

Peer group: age_band x income_band x home_region. Groups with fewer than 30 players
fall back to age_band x income_band, then to income_band alone.

Peer stats (data/features/peer_stats.parquet, long format): one row per peer group
per feature with n, median, q1, q3, iqr, p05, p95, mean, std, and the symlog median
and scale used for z-scores. For deposits, stake, bet frequency and deposit/income the
stats cover only peers active in the window (active_only = True).

Transaction flags (data/features/transaction_flags.parquet): txn_id, player_id and a
"|"-joined list of TXN_FLAGS codes (common.py) for every flagged transaction in the full
180 days: outside Ontario, impossible travel, first use of a device or payment method in
the current window, a deposit 5x the player's median, just under / reaching $10,000 within
24 hours, and low-odds bets (decimal odds under 1.30, a minimal-risk laundering pattern).

Usage:  python backend/pipeline/build_features.py
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from common import (FEATURES, INCOME_MIDPOINT, JURISDICTION, NEAR_THRESHOLD, REPORTING_THRESHOLD, SYNTH, TXN_FLAGS,
                    load_metadata, min_travel_hours, symlog)

MIN_PEER_GROUP = 30
PEER_Z_FEATURES = ["deposits_30d", "avg_stake_30d", "bets_per_day_30d", "net_loss_30d"]
PEER_STAT_FEATURES = PEER_Z_FEATURES + ["night_share_30d", "deposit_income_ratio", "distinct_ip_regions_30d"]
MIN_Z_SCALE = 0.5  # floor on the symlog spread: z = 3 always means at least ~4.5x the peer median
# Zero-inflated metrics (a third of players don't deposit in a given month) are compared
# with peers who were active in the window; otherwise the zeros swamp the spread.
ACTIVE_PEER_FEATURES = {"deposits_30d", "avg_stake_30d", "bets_per_day_30d", "deposit_income_ratio"}


def window_aggregates(t: pd.DataFrame, index: pd.Index) -> pd.DataFrame:
    out = pd.DataFrame(index=index)
    dep = t[t.type == "deposit"].groupby("player_id")["amount_cad"]
    out["deposits"], out["deposit_count"], out["max_deposit"] = dep.sum(), dep.count(), dep.max()
    out["withdrawals"] = t[t.type == "withdrawal"].groupby("player_id")["amount_cad"].sum()
    bets = t[t.type == "bet"]
    out["bets"] = bets.groupby("player_id").size()
    out["turnover"] = bets.groupby("player_id")["amount_cad"].sum()
    out["payouts"] = t[t.type == "payout"].groupby("player_id")["amount_cad"].sum()
    out["night_bets"] = bets[bets.timestamp.dt.hour < 6].groupby("player_id").size()
    return out.fillna(0.0)


def impossible_travel(t: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Flag transactions closer in time to the player's previous one than the travel time allows.

    `t` must be sorted by player and time and carry a `jur` column. Returns the mask and
    the previous transaction's timestamp / ip_region / jur, aligned to `t`.
    """
    prev = t.groupby("player_id")[["timestamp", "ip_region", "jur"]].shift()
    gap_h = (t.timestamp - prev.timestamp).dt.total_seconds() / 3600
    moved = prev.jur.notna() & t.jur.notna() & (prev.jur != t.jur)
    need_h = pd.Series(0.0, index=t.index)
    need_h[moved] = [min_travel_hours(a, b) for a, b in zip(prev.jur[moved], t.jur[moved])]
    return moved & (gap_h < need_h), prev


def location_features(tx: pd.DataFrame, players: pd.DataFrame, cur_start) -> pd.DataFrame:
    cur = tx[tx.timestamp >= cur_start].copy()
    cur["home"] = cur.player_id.map(players.set_index("player_id").home_region)
    cur["jur"] = cur.ip_region.map(JURISDICTION)
    g = cur.groupby("player_id")
    out = pd.DataFrame({
        "distinct_ip_regions_30d": g.ip_region.nunique(),
        "share_outside_home_region_30d": (cur.ip_region != cur.home).groupby(cur.player_id).mean(),
        "share_outside_ontario_30d": (cur.jur != "ON").groupby(cur.player_id).mean(),
        "out_of_province_txns_30d": (cur.jur != "ON").groupby(cur.player_id).sum(),
    })

    # Impossible travel: consecutive transactions in different jurisdictions, closer
    # in time than the minimum plausible travel time between them.
    cur = cur.sort_values(["player_id", "timestamp"], kind="stable")
    hit, prev = impossible_travel(cur)
    out["impossible_travel_count_30d"] = hit.groupby(cur.player_id).sum()
    first = cur[hit].groupby("player_id").head(1)
    p_first = prev.loc[first.index]
    out["impossible_travel_example"] = pd.Series(
        [f"{a} {ta:%Y-%m-%d %H:%M} -> {b} {tb:%H:%M} ({(tb - ta).total_seconds() / 60:.0f} min)"
         for a, ta, b, tb in zip(p_first.ip_region, p_first.timestamp, first.ip_region, first.timestamp)],
        index=first.player_id, dtype=object)

    # New devices / payment methods: first seen inside the current window.
    for col, name in [("device_id", "devices"), ("payment_method_id", "payment_methods")]:
        firsts = tx.dropna(subset=[col]).groupby(["player_id", col]).timestamp.min().reset_index()
        new = firsts[firsts.timestamp >= cur_start]
        out[f"new_{name}_30d"] = new.groupby("player_id").size()
        if col == "device_id":
            outside = cur[cur.jur != "ON"][["player_id", col]].drop_duplicates()
            out["new_devices_outside_ontario_30d"] = (
                new.merge(outside, on=["player_id", col]).groupby("player_id").size())
    return out


def deposit_windows(tx: pd.DataFrame) -> pd.DataFrame:
    """One row per deposit with the total, count and largest deposit of the 24 hours ending there."""
    dep = (tx[tx.type == "deposit"][["txn_id", "player_id", "timestamp", "amount_cad"]]
           .sort_values(["player_id", "timestamp"], kind="stable"))
    roll = dep.set_index("timestamp").groupby("player_id", sort=True)["amount_cad"].rolling("24h")
    dep["sum_24h"] = roll.sum().to_numpy()
    dep["count_24h"] = roll.count().to_numpy()
    dep["max_24h"] = roll.max().to_numpy()
    return dep


def episodes(hits: pd.DataFrame) -> pd.Series:
    """True for the first hit of each episode: no earlier hit by the same player in the 24 hours before."""
    prev = hits.groupby("player_id").timestamp.shift()
    return prev.isna() | (hits.timestamp - prev > pd.Timedelta(hours=24))


def compliance_features(dep: pd.DataFrame, cur_start, index: pd.Index) -> pd.DataFrame:
    cur = dep[dep.timestamp >= cur_start]
    hit = cur[cur.sum_24h >= REPORTING_THRESHOLD]
    split = hit[(hit.count_24h >= 2) & (hit.max_24h < REPORTING_THRESHOLD)]
    near = cur[(cur.amount_cad >= NEAR_THRESHOLD) & (cur.amount_cad < REPORTING_THRESHOLD)]
    out = pd.DataFrame({
        "threshold_24h_events_30d": hit[episodes(hit)].groupby("player_id").size(),
        "split_threshold_events_30d": split[episodes(split)].groupby("player_id").size(),
        "near_threshold_deposits_30d": near.groupby("player_id").size(),
        "max_deposits_24h_30d": cur.groupby("player_id").sum_24h.max(),
    }, index=index).fillna(0)
    top = hit.sort_values("sum_24h", ascending=False, kind="stable").groupby("player_id").head(1)
    example = [f"{ts:%Y-%m-%d}: {int(n)} deposit{'s' if n > 1 else ''} totalling ${total:,.2f} within 24 hours "
               f"(largest ${big:,.2f})" for ts, n, total, big in zip(top.timestamp, top.count_24h, top.sum_24h, top.max_24h)]
    out["threshold_24h_example"] = pd.Series(example, index=top.player_id.values, dtype=object).reindex(index).fillna("")
    return out


def transaction_flags(tx: pd.DataFrame, dep: pd.DataFrame, cur_start) -> pd.DataFrame:
    """Per-transaction flags (TXN_FLAGS codes) over the full period; flagged rows only."""
    t = tx.sort_values(["player_id", "timestamp"], kind="stable").copy()
    t["jur"] = t.ip_region.map(JURISDICTION)
    is_dep = t.type == "deposit"
    masks = {
        "OUTSIDE_ONTARIO": t.jur.notna() & (t.jur != "ON"),
        "IMPOSSIBLE_TRAVEL": impossible_travel(t)[0],
    }
    for col, code in [("device_id", "NEW_DEVICE"), ("payment_method_id", "NEW_PAYMENT_METHOD")]:
        first = t.dropna(subset=[col]).groupby(["player_id", col]).timestamp.idxmin()
        first = first[t.loc[first.values, "timestamp"].values >= cur_start]
        masks[code] = t.index.isin(first.values)
    median_dep = t[is_dep].groupby("player_id").amount_cad.median()
    masks["LARGE_DEPOSIT"] = is_dep & (t.amount_cad >= np.maximum(500, 5 * t.player_id.map(median_dep)))
    masks["NEAR_THRESHOLD"] = is_dep & (t.amount_cad >= NEAR_THRESHOLD) & (t.amount_cad < REPORTING_THRESHOLD)
    masks["THRESHOLD_24H"] = t.index.isin(dep.index[dep.sum_24h >= REPORTING_THRESHOLD])
    masks["LOW_ODDS_BET"] = (t.type == "bet") & (t.odds < 1.30) & (t.amount_cad >= 50)

    m = pd.DataFrame({code: np.asarray(masks[code], dtype=bool) for code in TXN_FLAGS}, index=t.index)
    flagged = m[m.any(axis=1)]
    codes = np.array(m.columns)
    return pd.DataFrame({
        "txn_id": t.loc[flagged.index, "txn_id"].values,
        "player_id": t.loc[flagged.index, "player_id"].values,
        "flags": ["|".join(codes[row]) for row in flagged.to_numpy()],
    })


def network_features(linked: pd.DataFrame, index: pd.Index) -> pd.DataFrame:
    shared = linked.groupby(["identifier_type", "identifier_value"]).player_id.agg(list)
    shared = shared[shared.map(len) > 1]
    graph = nx.Graph()
    graph.add_nodes_from(index)
    shared_count = pd.Series(0, index=index)
    for members in shared:
        for i, a in enumerate(members):
            shared_count[a] += 1
            for b in members[i + 1:]:
                graph.add_edge(a, b)
    cluster_id, cluster_size = {}, {}
    components = sorted((sorted(c) for c in nx.connected_components(graph)), key=lambda c: c[0])
    for k, comp in enumerate(components):
        for pid in comp:
            cluster_id[pid], cluster_size[pid] = f"C{k + 1:05d}", len(comp)
    return pd.DataFrame({
        "shared_identifier_count": shared_count,
        "linked_player_count": pd.Series(dict(graph.degree())),
        "network_cluster_id": pd.Series(cluster_id),
        "network_cluster_size": pd.Series(cluster_size),
    }, index=index)


def assign_peer_groups(players: pd.DataFrame) -> pd.DataFrame:
    levels = [
        ("age x income x region", players.age_band + " | " + players.income_band + " | " + players.home_region),
        ("age x income", players.age_band + " | " + players.income_band),
        ("income", players.income_band),
    ]
    group = pd.Series(np.nan, index=players.index, dtype=object)
    level = pd.Series(np.nan, index=players.index, dtype=object)
    for name, key in levels:
        sizes = key.map(key.value_counts())
        take = group.isna() & (sizes >= MIN_PEER_GROUP)
        group[take], level[take] = key[take], name
    rest = group.isna()  # tiny income bands: fall back to the broadest key anyway
    group[rest], level[rest] = levels[-1][1][rest], levels[-1][0]
    out = pd.DataFrame({"peer_group": group, "peer_group_level": level}, index=players.index)
    out["peer_group_size"] = out.peer_group.map(out.peer_group.value_counts())
    return out


def peer_stats(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for grp, sub in f.groupby("peer_group"):
        for feat in PEER_STAT_FEATURES:
            x = sub[feat].astype(float)
            active_only = feat in ACTIVE_PEER_FEATURES and (x > 0).sum() >= 10
            if active_only:
                x = x[x > 0]
            sx = symlog(x)
            q1, q3 = np.quantile(sx, [0.25, 0.75])
            rows.append({
                "peer_group": grp, "feature": feat, "n": len(x), "active_only": active_only,
                "median": x.median(), "q1": x.quantile(0.25), "q3": x.quantile(0.75),
                "iqr": x.quantile(0.75) - x.quantile(0.25),
                "p05": x.quantile(0.05), "p95": x.quantile(0.95),
                "mean": x.mean(), "std": x.std(ddof=0),
                "sym_median": float(np.median(sx)), "sym_scale": max((q3 - q1) / 1.349, MIN_Z_SCALE),
            })
    return pd.DataFrame(rows)


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    meta = load_metadata()
    players = pd.read_csv(SYNTH / "players.csv")
    tx = pd.read_csv(SYNTH / "transactions.csv", parse_dates=["timestamp"], dtype={"txn_id": str})
    linked = pd.read_csv(SYNTH / "linked_identifiers.csv")

    end = pd.Timestamp(meta["end_date"]) + pd.Timedelta(days=1)
    cur_start, base_start = end - pd.Timedelta(days=30), end - pd.Timedelta(days=120)
    idx = pd.Index(players.player_id, name="player_id")

    cur = window_aggregates(tx[tx.timestamp >= cur_start], idx)
    base = window_aggregates(tx[(tx.timestamp >= base_start) & (tx.timestamp < cur_start)], idx)

    f = players.set_index("player_id").copy()
    f["monthly_income_estimate"] = f.income_band.map(INCOME_MIDPOINT) / 12
    f["deposits_30d"] = cur.deposits
    f["deposit_count_30d"] = cur.deposit_count
    f["max_deposit_30d"] = cur.max_deposit
    f["withdrawals_30d"] = cur.withdrawals
    f["bets_30d"] = cur.bets
    f["turnover_30d"] = cur.turnover
    f["payouts_30d"] = cur.payouts
    f["net_loss_30d"] = cur.turnover - cur.payouts
    f["avg_stake_30d"] = (cur.turnover / cur.bets.where(cur.bets > 0)).fillna(0.0)
    f["bets_per_day_30d"] = cur.bets / 30
    f["night_share_30d"] = (cur.night_bets / cur.bets.where(cur.bets > 0)).fillna(0.0)
    f["deposits_base_30d"] = base.deposits / 3
    f["avg_stake_base"] = (base.turnover / base.bets.where(base.bets > 0)).fillna(0.0)
    f["bets_per_day_base"] = base.bets / 90
    f["net_loss_base_30d"] = (base.turnover - base.payouts) / 3
    f["night_share_base"] = (base.night_bets / base.bets.where(base.bets > 0)).fillna(0.0)

    f["deposit_income_ratio"] = f.deposits_30d / f.monthly_income_estimate
    f["deposit_change_ratio"] = f.deposits_30d / f.deposits_base_30d.clip(lower=50)
    f["stake_change_ratio"] = np.where(cur.bets > 0, f.avg_stake_30d / f.avg_stake_base.clip(lower=5), 1.0)
    f["night_share_change"] = f.night_share_30d - f.night_share_base
    f["loss_change_ratio"] = f.net_loss_30d.clip(lower=0) / f.net_loss_base_30d.clip(lower=50)
    f["withdrawal_to_deposit_ratio"] = (f.withdrawals_30d / f.deposits_30d.where(f.deposits_30d > 0)).fillna(0.0)
    f["turnover_to_deposit_ratio"] = (f.turnover_30d / f.deposits_30d.where(f.deposits_30d > 0)).fillna(0.0)

    loc = location_features(tx, players, cur_start)
    f = f.join(loc)
    count_cols = ["distinct_ip_regions_30d", "share_outside_home_region_30d", "share_outside_ontario_30d",
                  "out_of_province_txns_30d", "impossible_travel_count_30d", "new_devices_30d",
                  "new_devices_outside_ontario_30d", "new_payment_methods_30d"]
    f[count_cols] = f[count_cols].fillna(0)
    f["impossible_travel_example"] = f.impossible_travel_example.fillna("")

    dep = deposit_windows(tx)
    f = f.join(compliance_features(dep, cur_start, idx))
    flags = transaction_flags(tx, dep, cur_start)

    f = f.join(network_features(linked, idx))
    f["last_activity"] = tx.groupby("player_id").timestamp.max()

    f = f.join(assign_peer_groups(players.set_index("player_id")))
    stats = peer_stats(f)
    sym = stats.set_index(["peer_group", "feature"])
    for feat in PEER_Z_FEATURES:
        s = sym.xs(feat, level="feature")
        med, scale = f.peer_group.map(s.sym_median), f.peer_group.map(s.sym_scale)
        f[f"z_{feat}"] = (symlog(f[feat]) - med) / scale

    int_cols = ["deposit_count_30d", "bets_30d", "distinct_ip_regions_30d", "out_of_province_txns_30d",
                "threshold_24h_events_30d", "split_threshold_events_30d", "near_threshold_deposits_30d",
                "impossible_travel_count_30d", "new_devices_30d", "new_devices_outside_ontario_30d",
                "new_payment_methods_30d", "shared_identifier_count", "linked_player_count",
                "network_cluster_size", "peer_group_size"]
    f[int_cols] = f[int_cols].astype(int)
    return f.reset_index(), stats, flags


def main():
    f, stats, flags = build()
    FEATURES.mkdir(parents=True, exist_ok=True)
    f.to_parquet(FEATURES / "player_features.parquet", index=False)
    stats.to_parquet(FEATURES / "peer_stats.parquet", index=False)
    flags.to_parquet(FEATURES / "transaction_flags.parquet", index=False)
    numeric = f.select_dtypes("number")
    print(f"players={len(f)} features={f.shape[1]} peer_groups={f.peer_group.nunique()} "
          f"(levels: {f.peer_group_level.value_counts().to_dict()})")
    print(f"nulls in numeric features: {int(numeric.isna().sum().sum())}")
    counts = flags["flags"].str.split("|").explode().value_counts().to_dict()
    print(f"flagged transactions={len(flags)}: {counts}")


if __name__ == "__main__":
    main()
