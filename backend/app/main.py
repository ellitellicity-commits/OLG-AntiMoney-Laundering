"""Step 5 - FastAPI service for the investigator dashboard.

Reads the pipeline outputs (data/scores, data/features, data/synthetic) once at
startup and serves alerts, player detail, peer comparison, linked players, a weekly
activity timeline, per-transaction flags and a printable case report. The AI layer
(ai.py) adds grounded case summaries, case Q&A and plain-English queue search on a
free LLM provider, with non-LLM fallbacks.
Decisions are stored in data/decisions.json; /jube/* syncs them with Jube case management (docs/JUBE.md).

Run from the repo root:   uvicorn backend.app.main:app --reload
Interactive docs:         http://127.0.0.1:8000/docs
Dashboard (same server):  http://127.0.0.1:8000/app/
"""
from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.integrations.jube_router import make_jube_router
from backend.pipeline.common import BANDS, DATA, FEATURES, MODELS, ROOT, SCORES, SYNTH, TXN_FLAGS, load_metadata

from . import ai, report
from .schemas import (AISummary, AlertDetail, AlertList, AlertSummary, AskIn, AskOut, DecisionIn, DecisionOut, Meta,
                      Network, PeerComparison, PlayerDetail, SearchIn, SearchOut, Timeline)

DECISIONS_FILE = DATA / "decisions.json"
STATUS_FOR = {"accept": "In review", "escalate": "Escalated", "close": "Closed", "assign": "In review"}
BAND_ORDER = {name: i for i, (_, name) in enumerate(reversed(BANDS))}
PEER_CHART = [  # feature, baseline feature, label, unit
    ("deposits_30d", "deposits_base_30d", "30-day deposits", "money"),
    ("avg_stake_30d", "avg_stake_base", "Average stake", "money"),
    ("bets_per_day_30d", "bets_per_day_base", "Bets per day", "number"),
    ("net_loss_30d", "net_loss_base_30d", "30-day net loss", "money"),
    ("night_share_30d", "night_share_base", "Night betting share (00:00-05:59)", "percent"),
]
SUMMARY_FIELDS = [
    "deposits_30d", "deposits_base_30d", "withdrawals_30d", "turnover_30d", "net_loss_30d", "bets_30d",
    "avg_stake_30d", "deposit_income_ratio", "monthly_income_estimate", "distinct_ip_regions_30d",
    "out_of_province_txns_30d", "impossible_travel_count_30d", "new_devices_30d", "network_cluster_size",
]


class Store:
    """In-memory view of the pipeline outputs plus the decisions log."""

    def load(self):
        missing = [p for p in [SCORES / "alerts.json", SCORES / "risk_scores.csv",
                               FEATURES / "player_features.parquet", SYNTH / "transactions.csv"] if not p.exists()]
        if missing:
            raise RuntimeError("Pipeline outputs missing; run backend/pipeline/*.py first: "
                               + ", ".join(str(p.relative_to(ROOT)) for p in missing))
        self.meta = load_metadata()
        self.alerts = json.loads((SCORES / "alerts.json").read_text(encoding="utf-8"))
        wl = SCORES / "watchlist.json"
        self.watchlist = json.loads(wl.read_text(encoding="utf-8")) if wl.exists() else []
        both = self.alerts + self.watchlist
        self.alert_by_id = {a["alert_id"]: a for a in both}
        self.alert_by_player = {a["player_id"]: a for a in both}
        self.type_labels = {t: lbl for a in both for t, lbl in zip(a["anomaly_types"], a["anomaly_type_labels"])}
        xs = SCORES / "cross_seed.json"
        self.cross_seed = json.loads(xs.read_text(encoding="utf-8")) if xs.exists() else None
        self.scores = pd.read_csv(SCORES / "risk_scores.csv").set_index("player_id")
        self.features = pd.read_parquet(FEATURES / "player_features.parquet").set_index("player_id")
        self.peer_stats = pd.read_parquet(FEATURES / "peer_stats.parquet").set_index(["peer_group", "feature"])
        self.players = pd.read_csv(SYNTH / "players.csv").set_index("player_id")
        self.linked = pd.read_csv(SYNTH / "linked_identifiers.csv")
        tx = pd.read_csv(SYNTH / "transactions.csv", dtype={"txn_id": str, "player_id": str})
        self.tx = tx.sort_values(["player_id", "timestamp"], kind="stable").reset_index(drop=True)
        self.tx_index = self.tx.groupby("player_id").indices
        self.ts = pd.to_datetime(self.tx.timestamp)
        flags_path = FEATURES / "transaction_flags.parquet"
        flags = pd.read_parquet(flags_path) if flags_path.exists() else pd.DataFrame(columns=["txn_id", "flags"])
        self.txn_flags = dict(zip(flags.txn_id, flags["flags"].str.split("|")))
        card = MODELS / "model_card.json"
        self.model_card = json.loads(card.read_text(encoding="utf-8")) if card.exists() else None
        self.lock = threading.Lock()
        self.decisions: dict[str, list[dict]] = (
            json.loads(DECISIONS_FILE.read_text(encoding="utf-8")) if DECISIONS_FILE.exists() else {})

    def status(self, alert_id: str) -> str:
        hist = self.decisions.get(alert_id)
        return hist[-1]["status"] if hist else "New"

    def team(self, alert: dict) -> str:
        assigned = [d["team"] for d in self.decisions.get(alert["alert_id"], []) if d["decision"] == "assign"]
        return assigned[-1] if assigned else alert["team"]

    def save_decision(self, alert_id: str, record: dict):
        with self.lock:
            self.decisions.setdefault(alert_id, []).append(record)
            tmp = DECISIONS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.decisions, indent=1), encoding="utf-8")
            tmp.replace(DECISIONS_FILE)


store = Store()


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.load()
    yield


app = FastAPI(
    title="OLG Anti-Money Laundering: risk review API",
    description="Serves explainable risk alerts for sports-betting players. **All data is synthetic.**",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


def clean(v):
    """JSON-safe scalar: NaN -> None, numpy -> python."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, np.generic):
        v = v.item()
        return None if isinstance(v, float) and np.isnan(v) else v
    return v


def get_alert(alert_id: str) -> dict:
    alert = store.alert_by_id.get(alert_id)
    if not alert:
        raise HTTPException(404, f"Alert {alert_id} not found")
    return alert


def get_player(player_id: str):
    if player_id not in store.features.index:
        raise HTTPException(404, f"Player {player_id} not found")
    return store.features.loc[player_id]


def summary(a: dict) -> dict:
    return {**{k: a[k] for k in ["alert_id", "player_id", "score", "band", "anomaly_types",
                                 "anomaly_type_labels", "top_reason", "last_activity", "points_total"]},
            "kind": a.get("kind", "alert"), "confidence": (a.get("confidence") or {}).get("level"),
            "team": store.team(a), "status": store.status(a["alert_id"]),
            "recommended_action": a["recommended_action"]["action"],
            "ml_probability": (a.get("ml") or {}).get("probability")}


def priority(r: dict) -> tuple:
    """Queue order for equal scores: total points, then the AI model's probability."""
    return (r["score"], r["points_total"], r["ml_probability"] or 0)


def txn_rows(rows: pd.DataFrame) -> list[dict]:
    out = []
    for row in rows.to_dict("records"):
        t = {k: clean(v) for k, v in row.items() if k != "player_id"}
        t["flags"] = store.txn_flags.get(t["txn_id"], [])
        out.append(t)
    return out


def case_file(a: dict) -> dict:
    """Compact, LLM-ready view of everything computed about one alert (and nothing else)."""
    pid = a["player_id"]
    f = store.features.loc[pid]
    peers = player_peers(pid)
    net = player_network(pid)
    idx = store.tx_index.get(pid, np.array([], dtype=int))
    flag_counts: dict[str, int] = {}
    for txn_id in store.tx.txn_id.iloc[idx]:
        for code in store.txn_flags.get(txn_id, []):
            flag_counts[TXN_FLAGS.get(code, code)] = flag_counts.get(TXN_FLAGS.get(code, code), 0) + 1
    def r2(v):
        return round(v, 2) if isinstance(v, float) else v

    ml = a.get("ml")
    return {
        "alert_id": a["alert_id"], "player_id": pid, "score": a["score"], "band": a["band"],
        "team": store.team(a), "status": store.status(a["alert_id"]),
        "profile": a["profile"], "peer_group": a["peer_group"], "window": a["window"],
        "reasons": [{k: r[k] for k in ["title", "detail", "points", "anomaly_type", "comparison"]} for r in a["reasons"]],
        "recommended_action": a["recommended_action"],
        "confidence": a.get("confidence"), "mitigating_factors": a.get("mitigating", []),
        "behaviour_group": a.get("behaviour_group"),
        "ai_model": None if not ml else {
            "probability": ml["probability"],
            "drivers": [{"feature": d["label"], "value": d["value"]} for d in ml["drivers"]]},
        "key_figures_30d": {k: r2(clean(f[k])) for k in SUMMARY_FIELDS},
        "peer_comparison": [{"metric": m["label"], "last_30_days": r2(m["current"]), "own_baseline": r2(m["baseline"]),
                             "peer_median": r2(m["peer"]["median"]), "peer_z": r2(m["z"])} for m in peers["metrics"]],
        "linked_accounts": {"cluster_size": net["cluster_size"], "accounts": [
            {"player_id": l["player_id"], "score": l["score"], "band": l["band"],
             "shared": sorted({s["identifier_type"] for s in l["shared"]})} for l in net["linked_players"][:8]]},
        "flagged_transactions_180d": flag_counts,
        "decisions": [{k: d[k] for k in ["decision", "status", "note", "recorded_at"]}
                      for d in store.decisions.get(a["alert_id"], [])[-5:]],
    }


# --- Endpoints ---------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/meta", response_model=Meta)
def meta():
    return {
        "synthetic": True, "window_start": store.meta["start_date"], "window_end": store.meta["end_date"],
        "players": len(store.players), "alerts": len(store.alerts), "watchlist": len(store.watchlist),
        "bands": [name for _, name in reversed(BANDS)], "teams": ["AML", "Fraud", "Safer Gambling"],
        "anomaly_types": store.type_labels, "statuses": ["New", "In review", "Escalated", "Closed"],
        "transaction_flags": TXN_FLAGS, "ai": ai.llm.status(),
    }


@app.get("/alerts", response_model=AlertList)
def list_alerts(
    band: str | None = Query(None, description="Low / Medium / High / Critical"),
    team: str | None = Query(None, description="AML / Fraud / Safer Gambling"),
    type: str | None = Query(None, description="Anomaly type, e.g. income_mismatch"),
    status: str | None = Query(None, description="New / In review / Escalated / Closed"),
    q: str | None = Query(None, description="Search player or alert ID"),
    min_score: int | None = Query(None, ge=0, le=100, description="Only alerts scoring at least this"),
    confidence: str | None = Query(None, description="High / Medium / Low"),
    sort: str = Query("-score", description="Field to sort by; prefix with - for descending. score (ties broken "
                                            "by total points, then AI probability), ai, player_id, team, status, "
                                            "last_activity, band"),
    include_watchlist: bool = Query(False, description="Also return watchlist entries (below the alert line)"),
    limit: int = Query(500, ge=1, le=5000),
):
    rows = [summary(a) for a in store.alerts + (store.watchlist if include_watchlist else [])]
    if confidence:
        rows = [r for r in rows if r["confidence"] == confidence]
    if band:
        rows = [r for r in rows if r["band"] == band]
    if team:
        rows = [r for r in rows if r["team"] == team]
    if type:
        rows = [r for r in rows if type in r["anomaly_types"]]
    if status:
        rows = [r for r in rows if r["status"] == status]
    if min_score is not None:
        rows = [r for r in rows if r["score"] >= min_score]
    if q:
        needle = q.strip().upper()
        rows = [r for r in rows if needle in r["player_id"] or needle in r["alert_id"]]
    key, desc = sort.lstrip("-"), sort.startswith("-")
    sorters = {
        "score": priority, "ai": lambda r: r["ml_probability"] or 0,
        "player_id": lambda r: r["player_id"], "team": lambda r: r["team"],
        "status": lambda r: r["status"], "last_activity": lambda r: r["last_activity"] or "",
        "band": lambda r: BAND_ORDER[r["band"]], "top_reason": lambda r: r["top_reason"]["title"],
    }
    if key not in sorters:
        raise HTTPException(400, f"Unknown sort field {key!r}")
    rows.sort(key=lambda r: r["player_id"])  # stable tie-break
    rows.sort(key=sorters[key], reverse=desc)
    return {"total": len(rows), "alerts": rows[:limit]}


@app.get("/alerts/{alert_id}", response_model=AlertDetail)
def alert_detail(alert_id: str):
    a = get_alert(alert_id)
    return {**a, "team": store.team(a), "status": store.status(alert_id),
            "decisions": store.decisions.get(alert_id, [])}


@app.post("/alerts/{alert_id}/decision", response_model=DecisionOut)
def record_decision(alert_id: str, body: DecisionIn):
    a = get_alert(alert_id)
    if body.decision == "close" and not body.note.strip():
        raise HTTPException(422, "A reason is required to close an alert")
    if body.decision == "assign" and not body.team:
        raise HTTPException(422, "A team is required to assign an alert")
    if not body.investigator.strip():
        raise HTTPException(422, "Enter the investigator's name: every decision is recorded in the audit trail")
    record = {
        "decision": body.decision, "note": body.note.strip(), "team": body.team,
        "investigator": body.investigator.strip(), "status": STATUS_FOR[body.decision],
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    store.save_decision(alert_id, record)
    return {"alert_id": alert_id, "status": record["status"], "team": store.team(a), "decision": record}


# --- Jube case management (optional; inert until JUBE_URL / JUBE_MODEL_GUID are set, see docs/JUBE.md) ---

JUBE_METRICS = ["deposits_30d", "withdrawals_30d", "turnover_30d", "net_loss_30d"]


def jube_alerts() -> list[dict]:
    """Alerts in the shape backend/integrations/jube.py expects, with the 30-day money figures added."""
    out = []
    for a in store.alerts:
        f = store.features.loc[a["player_id"]] if a["player_id"] in store.features.index else None
        out.append({**a, "team": store.team(a), "created_at": a.get("last_activity") or store.meta["end_date"],
                    "key_metrics": {} if f is None else {k: clean(f[k]) or 0 for k in JUBE_METRICS}})
    return out


def jube_decision(alert_id: str, d: dict):
    """Store a decision pulled from a Jube case exactly like one made in the dashboard."""
    if alert_id not in store.alert_by_id:
        return
    store.save_decision(alert_id, {
        "decision": d["decision"], "note": d.get("note") or d.get("reason") or "", "team": None,
        "investigator": f"{d.get('investigator') or 'unknown'} (via Jube)", "status": STATUS_FOR[d["decision"]],
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    })


app.include_router(make_jube_router(get_alerts=jube_alerts, record_decision=jube_decision))


@app.get("/players/{player_id}", response_model=PlayerDetail)
def player_detail(player_id: str, limit: int = Query(50, ge=1, le=1000),
                  flagged_only: bool = Query(False, description="Only transactions with at least one flag")):
    f = get_player(player_id)
    p = store.players.loc[player_id]
    s = store.scores.loc[player_id]
    idx = store.tx_index.get(player_id, np.array([], dtype=int))
    rows = store.tx.iloc[idx].iloc[::-1]
    if flagged_only:
        rows = rows[rows.txn_id.isin(store.txn_flags.keys())]
    txns = txn_rows(rows.head(limit))
    alert = store.alert_by_player.get(player_id)
    return {
        "player_id": player_id,
        "profile": {k: clean(p[k]) for k in ["age_band", "occupation", "income_band", "home_region", "signup_date",
                                             "kyc_status", "pep", "sanctions_screening"]},
        "peer_group": f.peer_group, "score": int(s.score), "band": s.band,
        "alert_id": alert["alert_id"] if alert else None,
        "summary": {k: clean(f[k]) for k in SUMMARY_FIELDS},
        "transactions_total": len(rows), "transactions": txns,
    }


@app.get("/players/{player_id}/peers", response_model=PeerComparison)
def player_peers(player_id: str):
    f = get_player(player_id)
    metrics = []
    for feat, base, label, unit in PEER_CHART:
        st = store.peer_stats.loc[(f.peer_group, feat)]
        z = f.get(f"z_{feat}")
        metrics.append({
            "feature": feat, "label": label, "unit": unit, "current": clean(f[feat]),
            "baseline": clean(f[base]), "z": clean(z) if z is not None else None,
            "peer": {"n": int(st.n), "active_only": bool(st.active_only),
                     **{k: clean(st[k]) for k in ["median", "q1", "q3", "p05", "p95"]}},
        })
    behaviour = {
        "name": f.behaviour_cluster_name, "size": int(f.behaviour_cluster_size),
        "metrics": [{"feature": feat, "label": label, "current": clean(f[feat]),
                     "median": clean(f[f"cluster_median_{feat}"]), "z": clean(f[f"z_cluster_{feat}"])}
                    for feat, label in [("deposits_30d", "30-day deposits"), ("avg_stake_30d", "Average stake")]],
    } if f.behaviour_cluster >= 0 else None
    return {"player_id": player_id, "peer_group": f.peer_group, "peer_group_level": f.peer_group_level,
            "peer_group_size": int(f.peer_group_size), "metrics": metrics, "behaviour_group": behaviour}


@app.get("/players/{player_id}/network", response_model=Network)
def player_network(player_id: str):
    f = get_player(player_id)
    linked = store.linked
    mine = linked[linked.player_id == player_id][["identifier_type", "identifier_value"]]
    shared = linked.merge(mine, on=["identifier_type", "identifier_value"])
    shared = shared[shared.player_id != player_id]
    out = []
    for pid, grp in shared.groupby("player_id"):
        s = store.scores.loc[pid]
        alert = store.alert_by_player.get(pid)
        out.append({"player_id": pid, "score": int(s.score), "band": s.band,
                    "alert_id": alert["alert_id"] if alert else None,
                    "shared": grp[["identifier_type", "identifier_value"]].to_dict("records")})
    out.sort(key=lambda r: (-r["score"], r["player_id"]))
    return {"player_id": player_id, "cluster_id": f.network_cluster_id,
            "cluster_size": int(f.network_cluster_size), "linked_players": out}


@app.get("/players/{player_id}/timeline", response_model=Timeline)
def player_timeline(player_id: str):
    """Weekly activity over the full 180 days, so behaviour change over time is visible."""
    get_player(player_id)
    end = pd.Timestamp(store.meta["end_date"]) + pd.Timedelta(days=1)
    start = end - pd.Timedelta(weeks=26)
    idx = store.tx_index.get(player_id, np.array([], dtype=int))
    t = store.tx.iloc[idx].assign(ts=store.ts.iloc[idx].values)
    t = t[t.ts >= start]
    week = ((t.ts - start).dt.days // 7).astype(int)
    amount = t.amount_cad.astype(float)
    is_bet = t.type == "bet"
    frame = pd.DataFrame({
        "deposits": amount.where(t.type == "deposit", 0.0), "withdrawals": amount.where(t.type == "withdrawal", 0.0),
        "turnover": amount.where(is_bet, 0.0), "payouts": amount.where(t.type == "payout", 0.0),
        "bets": is_bet.astype(int), "night_bets": (is_bet & (t.ts.dt.hour < 6)).astype(int),
        "outside_ontario_txns": t.txn_id.map(lambda x: "OUTSIDE_ONTARIO" in store.txn_flags.get(x, ())).astype(int),
        "flagged_txns": t.txn_id.isin(store.txn_flags.keys()).astype(int),
        "week": week,
    }).groupby("week").sum().reindex(range(26), fill_value=0)
    weeks = [{
        "week_start": (start + pd.Timedelta(weeks=int(w))).date().isoformat(),
        "deposits": round(float(r.deposits), 2), "withdrawals": round(float(r.withdrawals), 2),
        "turnover": round(float(r.turnover), 2), "net_loss": round(float(r.turnover - r.payouts), 2),
        "bets": int(r.bets), "night_share": round(float(r.night_bets / r.bets), 3) if r.bets else 0.0,
        "outside_ontario_txns": int(r.outside_ontario_txns), "flagged_txns": int(r.flagged_txns),
    } for w, r in frame.iterrows()]
    return {"player_id": player_id, "weeks": weeks,
            "current_window_start": (end - pd.Timedelta(days=30)).date().isoformat(),
            "baseline_start": (end - pd.Timedelta(days=120)).date().isoformat()}


@app.get("/stats")
def stats():
    """Queue-wide counts for an overview panel (bands, teams, types, statuses, compliance, AI model)."""
    rows = [summary(a) for a in store.alerts]

    def count(key, many=False):
        out: dict[str, int] = {}
        for r in rows:
            for v in (r[key] if many else [r[key]]):
                out[v] = out.get(v, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))
    codes = [x["code"] for a in store.alerts for x in a["reasons"]]
    compliance = {label: codes.count(code) for code, label in [
        ("STRUCTURING", "Structuring"), ("LARGE_TRANSACTION_24H", "$10,000+ in 24 hours"),
        ("SANCTIONS_SCREENING", "Sanctions screening match"), ("KYC_UNVERIFIED", "Unverified identity"),
        ("PEP_EDD", "PEP enhanced due diligence"), ("THIRD_PARTY_FUNDING", "Third-party funding"),
        ("UTURN_WITHDRAWAL", "U-turn withdrawals"), ("DORMANT_REACTIVATION", "Dormant account reactivated")]}
    mc = store.model_card or {}
    return {
        "players": len(store.players), "alerts": len(rows), "watchlist": len(store.watchlist),
        "by_band": count("band"), "by_team": count("team"), "by_status": count("status"),
        "by_confidence": count("confidence"),
        "by_anomaly_type": {store.type_labels.get(k, k): v for k, v in count("anomaly_types", many=True).items()},
        "compliance": compliance,
        "ai_model_alerts": codes.count("ML_MODEL"),
        "flagged_transactions": len(store.txn_flags),
        "trends": flag_trends(),
        "ai_model": {"metrics": mc.get("metrics"), "top_features": [g["label"] for g in mc.get("global_importance", [])[:6]],
                     "cross_seed": store.cross_seed},
    }


def flag_trends(weeks: int = 13) -> dict:
    """Weekly counts of each transaction flag, with the last 4 weeks vs the 9 before ("emerging risk")."""
    end = pd.Timestamp(store.meta["end_date"]) + pd.Timedelta(days=1)
    start = end - pd.Timedelta(weeks=weeks)
    flagged = store.tx[store.tx.txn_id.isin(store.txn_flags.keys())]
    ts = store.ts[flagged.index]
    keep = ts >= start
    week = ((ts[keep] - start).dt.days // 7).astype(int)
    counts: dict[str, list[int]] = {code: [0] * weeks for code in TXN_FLAGS}
    for txn_id, w in zip(flagged.txn_id[keep], week):
        for code in store.txn_flags[txn_id]:
            counts[code][w] += 1
    out = []
    for code, series in counts.items():
        recent, before = sum(series[-4:]) / 4, sum(series[:-4]) / max(1, weeks - 4)
        change = None if before == 0 else round(recent / before - 1, 3)
        out.append({"flag": code, "label": TXN_FLAGS[code], "weekly": series,
                    "recent_weekly_avg": round(recent, 1), "earlier_weekly_avg": round(before, 1),
                    "change": change, "rising": bool(before and recent >= 1.5 * before and recent >= 3)})
    week_starts = [(start + pd.Timedelta(weeks=i)).date().isoformat() for i in range(weeks)]
    return {"weeks": week_starts, "flags": sorted(out, key=lambda x: -(x["change"] or 0))}


@app.get("/watchlist", response_model=AlertList)
def watchlist():
    """Players below the alert line whose pattern the AI models find very unusual or risk-like."""
    rows = sorted((summary(a) for a in store.watchlist), key=priority, reverse=True)
    return {"total": len(rows), "alerts": rows}


@app.get("/audit")
def audit():
    """Every recorded decision, newest first: who decided what, when, and why."""
    rows = [{"alert_id": aid, **d, "player_id": store.alert_by_id.get(aid, {}).get("player_id")}
            for aid, hist in store.decisions.items() for d in hist]
    rows.sort(key=lambda d: d["recorded_at"], reverse=True)
    return {"total": len(rows), "decisions": rows}


@app.get("/audit.csv", response_class=PlainTextResponse)
def audit_csv():
    """The audit trail as CSV (open in Excel)."""
    cols = ["recorded_at", "alert_id", "player_id", "decision", "status", "team", "investigator", "note"]
    df = pd.DataFrame(audit()["decisions"], columns=cols)
    return PlainTextResponse(df.to_csv(index=False), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=audit_trail.csv"})


@app.get("/model")
def model_card():
    """Model card for the supervised AI model: metrics, top features, caveats."""
    if not store.model_card:
        raise HTTPException(404, "No model card; run backend/pipeline/train_model.py")
    return store.model_card


# --- AI layer (free LLM providers; every feature has a non-LLM fallback) -----------------

@app.get("/ai/status")
def ai_status():
    return ai.llm.status()


@app.get("/alerts/{alert_id}/summary", response_model=AISummary)
def alert_summary(alert_id: str, refresh: bool = Query(False, description="Ignore the cache and regenerate")):
    """Plain-language case summary. Every number is checked against the case file; failures fall back
    to a deterministic template."""
    return ai.summarize(case_file(get_alert(alert_id)), refresh=refresh)


@app.post("/alerts/{alert_id}/ask", response_model=AskOut)
def alert_ask(alert_id: str, body: AskIn):
    """Ask a question about one case. The model sees only that case's computed evidence."""
    return ai.ask(case_file(get_alert(alert_id)), body.question.strip(), body.history)


@app.post("/ai/search", response_model=SearchOut)
def ai_search(body: SearchIn):
    """Turn a plain-English request ("critical AML alerts with linked players") into queue filters."""
    m = meta()
    parsed = ai.parse_search(body.query, m)

    def run(f: dict) -> dict:
        return list_alerts(band=f.get("band"), team=f.get("team"), type=f.get("type"), status=f.get("status"),
                           q=f.get("q"), min_score=f.get("min_score"), sort=f.get("sort", "-score"), limit=5000)
    result = run(parsed["filters"])
    if parsed["source"] == "llm" and result["total"] == 0 and parsed["filters"]:
        # The model's reading matched nothing: show everything rather than an empty queue, and say so.
        parsed = {**parsed, "filters": {}, "explanation": "no filters (the AI's reading of this request matched no "
                  "alerts, so all alerts are shown)"}
        result = run({})
    return {"query": body.query, **parsed, **result}


@app.get("/alerts/{alert_id}/report", response_class=HTMLResponse)
def alert_report(alert_id: str):
    """Printable case report (HTML; print or save as PDF from the browser)."""
    a = get_alert(alert_id)
    pid = a["player_id"]
    detail = alert_detail(alert_id)
    idx = store.tx_index.get(pid, np.array([], dtype=int))
    rows = store.tx.iloc[idx].iloc[::-1]
    flagged = txn_rows(rows[rows.txn_id.isin(store.txn_flags.keys())])
    summ = ai.summarize(case_file(a), use_llm=False)
    html = report.render(detail, player_detail(pid, limit=1, flagged_only=False), player_peers(pid),
                         player_network(pid), flagged, summ,
                         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    return HTMLResponse(html)


# --- Dashboard (same origin, so no CORS or file:// issues) ----------------------------

FRONTEND = ROOT / "frontend"
if FRONTEND.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND, html=True), name="app")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app/")
