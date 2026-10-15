"""FastAPI service for the investigator dashboard.

Run from the repo root:
    uvicorn backend.app.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs

All data served is synthetic (see the X-Data-Source response header).
"""
from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from backend.app import schemas
from backend.app.network import get_graph
from backend.app.store import STATUS_FOR, DataNotReady, DataStore
from backend.pipeline.common import ALERT_MIN_SCORE, ANOMALY_TYPES, BANDS
from backend.pipeline.detect import ACTIONS, PEER_LABELS, TEAM_BY_TYPE, WEIGHTS

store = DataStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        store.warm()
    except DataNotReady as e:  # still start so /health and /docs work; data endpoints return 503
        print(f"[warning] {e}")
    yield


app = FastAPI(
    title="OLG Anti-Money Laundering: Investigator API",
    description="Risk-ranked alerts, evidence, peer comparisons, player networks and investigator decisions. "
                "**All data is synthetic.**",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def synthetic_header(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Data-Source"] = "synthetic"
    return resp


@app.exception_handler(DataNotReady)
async def data_not_ready(_: Request, exc: DataNotReady):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def clean(v):
    """Make numpy / pandas values JSON-safe."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 4)
    if isinstance(v, (pd.Timestamp,)):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if v is pd.NA or v is None:
        return None
    return v


def status_of(alert_id: str, latest: dict[str, dict]) -> str:
    d = latest.get(alert_id)
    return STATUS_FOR[d["decision"]] if d else "open"


def get_alert_or_404(alert_id: str) -> dict:
    a = store.alerts_by_id.get(alert_id)
    if not a:
        raise HTTPException(404, f"Alert {alert_id} not found")
    return a


def require_player(pid: str):
    if pid not in store.features.index:
        raise HTTPException(404, f"Player {pid} not found")


def txn_records(df: pd.DataFrame) -> list[dict]:
    out = []
    for rec in df.to_dict(orient="records"):
        out.append({k: clean(v) for k, v in rec.items()})
    return out


def summarize(a: dict, latest: dict[str, dict]) -> dict:
    return {
        "alert_id": a["alert_id"], "player_id": a["player_id"], "rank": a["rank"], "score": a["score"],
        "band": a["band"], "team": a["team"], "anomaly_types": a["anomaly_types"],
        "top_reason_code": a["top_reason_code"], "top_reason_title": a["reasons"][0]["title"],
        "reason_count": len(a["reasons"]), "status": status_of(a["alert_id"], latest),
        "profile": a["profile"], "recommended_action": a["recommended_action"]["action"], "created_at": a["created_at"],
    }


# --------------------------------------------------------------------------------------
# meta
# --------------------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/meta", tags=["meta"])
def meta():
    """Reference data for building filters and legends in the UI."""
    return {
        "bands": [{"name": n, "min": c} for c, n in BANDS],
        "alert_min_score": ALERT_MIN_SCORE,
        "anomaly_types": ANOMALY_TYPES + ["cash_cycling", "linked_players", "multivariate_outlier"],
        "teams": sorted(set(TEAM_BY_TYPE.values()) | {"Safer Gambling"}),
        "actions": {k: {"action": v[0], "rationale": v[1]} for k, v in ACTIONS.items()},
        "peer_features": PEER_LABELS,
        "weights": WEIGHTS,
        "decisions": list(STATUS_FOR),
        "synthetic": True,
    }


@app.get("/stats", response_model=schemas.Stats, tags=["meta"])
def stats():
    """Queue-level counts for the dashboard header."""
    latest = store.latest_decisions()
    alerts = store.alerts
    by_type: dict[str, int] = {}
    for a in alerts:
        for t in a["anomaly_types"]:
            by_type[t] = by_type.get(t, 0) + 1
    by_status = {"open": 0, "accepted": 0, "escalated": 0, "closed": 0}
    for a in alerts:
        by_status[status_of(a["alert_id"], latest)] += 1
    s = store.scores["score"]
    hist = [{"from": b, "to": b + 9, "players": int(((s >= b) & (s <= b + 9)).sum())} for b in range(0, 100, 10)]
    hist[-1]["to"] = 100
    hist[-1]["players"] = int(((s >= 90) & (s <= 100)).sum())
    return {
        "reference_date": store.reference_date.date().isoformat(), "players": int(len(s)), "alerts": len(alerts),
        "by_band": {n: sum(1 for a in alerts if a["band"] == n) for _, n in BANDS},
        "by_team": {t: sum(1 for a in alerts if a["team"] == t) for t in sorted({a["team"] for a in alerts})},
        "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])), "by_status": by_status,
        "score_histogram": hist, "synthetic": True,
    }


@app.get("/validation", tags=["meta"])
def validation():
    """Detection quality against the injected ground truth (output of validate.py)."""
    return store.validation


# --------------------------------------------------------------------------------------
# alerts
# --------------------------------------------------------------------------------------
@app.get("/alerts", response_model=schemas.AlertList, tags=["alerts"])
def list_alerts(
    band: Optional[str] = Query(None, description="Comma-separated: Critical,High,Medium,Low"),
    team: Optional[str] = Query(None, description="AML, Fraud or Safer Gambling (comma-separated)"),
    type: Optional[str] = Query(None, description="Anomaly type, e.g. income_mismatch (comma-separated, any match)"),
    status: Optional[str] = Query(None, description="open, accepted, escalated, closed (comma-separated)"),
    q: Optional[str] = Query(None, description="Search player ID, occupation, region or reason code"),
    min_score: int = Query(0, ge=0, le=100),
    sort: str = Query("-score", description="score, -score, player_id, -player_id, rank"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Ranked alert queue (summary fields). Default order: highest risk first."""
    latest = store.latest_decisions()
    split = lambda s: {x.strip().lower() for x in s.split(",") if x.strip()} if s else None  # noqa: E731
    bands, teams, types, statuses = split(band), split(team), split(type), split(status)
    items = []
    for a in store.alerts:
        if a["score"] < min_score:
            continue
        if bands and a["band"].lower() not in bands:
            continue
        if teams and a["team"].lower() not in teams:
            continue
        if types and not types & set(a["anomaly_types"]):
            continue
        st = status_of(a["alert_id"], latest)
        if statuses and st not in statuses:
            continue
        if q:
            hay = " ".join([a["player_id"], a["profile"]["occupation"], a["profile"]["home_region"],
                            " ".join(r["code"] for r in a["reasons"])]).lower()
            if q.lower() not in hay:
                continue
        items.append(a)
    key, rev = sort.lstrip("-"), sort.startswith("-")
    if key not in {"score", "player_id", "rank"}:
        raise HTTPException(400, "sort must be one of score, -score, player_id, -player_id, rank, -rank")
    if key == "score":
        items.sort(key=lambda a: (a["score"], -a["rank"]), reverse=rev)
    else:
        items.sort(key=lambda a: a[key], reverse=rev)
    page = items[offset: offset + limit]
    return {"total": len(items), "limit": limit, "offset": offset, "items": [summarize(a, latest) for a in page]}


@app.get("/alerts/export.csv", tags=["alerts"], response_class=PlainTextResponse)
def export_alerts():
    """The full queue as CSV, with current status, for spreadsheets or case-management import."""
    latest = store.latest_decisions()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["rank", "alert_id", "player_id", "score", "band", "team", "status", "anomaly_types",
                "top_reason_code", "recommended_action", "summary"])
    for a in store.alerts:
        w.writerow([a["rank"], a["alert_id"], a["player_id"], a["score"], a["band"], a["team"],
                    status_of(a["alert_id"], latest), ";".join(a["anomaly_types"]), a["top_reason_code"],
                    a["recommended_action"]["action"], a["summary"]])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=alerts_synthetic.csv"})


@app.get("/alerts/{alert_id}", response_model=schemas.Alert, tags=["alerts"])
def get_alert(alert_id: str):
    """Full alert: reasons with evidence, peer/baseline comparison, recommended action, latest decision."""
    a = get_alert_or_404(alert_id)
    latest = store.latest_decisions()
    return {**a, "status": status_of(alert_id, latest), "latest_decision": latest.get(alert_id)}


@app.post("/alerts/{alert_id}/decision", response_model=schemas.DecisionOut, status_code=201, tags=["alerts"])
def record_decision(alert_id: str, body: schemas.DecisionIn):
    """Record an investigator decision: accept / escalate / close, with a note.
    Closing an alert requires a reason (e.g. 'benign household', 'verified source of funds')."""
    get_alert_or_404(alert_id)
    if body.decision == "close" and not (body.reason or body.note).strip():
        raise HTTPException(422, "Closing an alert requires a reason or note")
    return store.add_decision(alert_id, body.decision, body.note, body.reason, body.investigator)


@app.get("/alerts/{alert_id}/decisions", response_model=list[schemas.DecisionOut], tags=["alerts"])
def decision_history(alert_id: str):
    """Audit trail of every decision recorded on the alert, oldest first."""
    get_alert_or_404(alert_id)
    return store.decisions_for(alert_id)


@app.get("/alerts/{alert_id}/report", response_class=PlainTextResponse, tags=["alerts"])
def alert_report(alert_id: str):
    """A printable case summary in Markdown, built only from computed evidence."""
    a = get_alert_or_404(alert_id)
    p = a["profile"]
    km = a["key_metrics"]
    lines = [
        f"# Case summary: {a['alert_id']}", "",
        "_SYNTHETIC DATA: for demonstration only._", "",
        f"**Player:** {a['player_id']} | {p['age_band']} | {p['occupation']} | {p['income_band']} | {p['home_region']}",
        f"**Risk score:** {a['score']}/100 ({a['band']}) | rank {a['rank']} | team: {a['team']}",
        f"**Peer group:** {a['peer_group']} (n={a['peer_group_size']})", "",
        "## Why flagged", "",
    ]
    for r in a["reasons"]:
        comp = r["comparison"]
        extra = []
        if comp.get("own_baseline") is not None:
            extra.append(f"own baseline {comp['own_baseline']:,.2f}")
        if comp.get("peer_median") is not None:
            extra.append(f"peer median {comp['peer_median']:,.2f}")
        lines.append(f"- **{r['title']}** (+{r['points']}, `{r['code']}`): {r['detail']}"
                     + (f" _[{'; '.join(extra)}]_" if extra else ""))
    lines += ["", "## Key metrics (last 30 days)", "",
              f"| Deposits | Withdrawals | Staked | Net loss | Bets | Avg stake | Usual deposits / 30d | Est. monthly income |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|",
              f"| ${km['deposits_30d']:,.2f} | ${km['withdrawals_30d']:,.2f} | ${km['turnover_30d']:,.2f} | "
              f"${km['net_loss_30d']:,.2f} | {km['bet_count_30d']:.0f} | ${km['avg_stake_30d']:,.2f} | "
              f"${km['deposits_baseline_m']:,.2f} | ${km['monthly_income_estimate']:,.2f} |", "",
              "## Recommended action", "",
              f"**{a['recommended_action']['action']}** ({a['recommended_action']['team']}). {a['recommended_action']['rationale']}"]
    for s in a["recommended_action"]["secondary"]:
        lines.append(f"- Also: {s['action']} ({s['team']})")
    hist = store.decisions_for(alert_id)
    lines += ["", "## Decision history", ""]
    lines += [f"- {d['created_at']}: **{d['decision']}** by {d['investigator'] or 'unknown'}"
              + (f" | reason: {d['reason']}" if d["reason"] else "") + (f" | {d['note']}" if d["note"] else "")
              for d in hist] or ["- No decisions recorded yet."]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/markdown")


# --------------------------------------------------------------------------------------
# players
# --------------------------------------------------------------------------------------
FEATURE_FIELDS = [
    "deposits_30d", "deposit_count_30d", "max_deposit_30d", "withdrawals_30d", "turnover_30d", "payouts_30d",
    "net_loss_30d", "bet_count_30d", "avg_stake_30d", "bets_per_day_30d", "active_days_30d", "night_share_30d",
    "deposit_to_income", "withdrawal_to_deposit_30d", "turnover_to_deposit_30d", "chase_deposits_30d",
    "deposits_baseline_m", "avg_stake_baseline", "bets_per_day_baseline", "night_share_baseline", "net_loss_baseline_m",
    "deposit_change_ratio", "stake_change_ratio", "activity_change_ratio", "night_share_change",
    "distinct_ip_regions_30d", "share_outside_home_30d", "share_outside_canada_30d", "impossible_travel_count_30d",
    "new_devices_30d", "new_payment_methods_30d", "withdrawals_to_new_pm_30d", "shared_identifier_count",
    "linked_players", "opposite_bets_with_linked",
]
BASELINE_FOR = {"deposits_30d": "deposits_baseline_m", "avg_stake_30d": "avg_stake_baseline",
                "bets_per_day_30d": "bets_per_day_baseline", "net_loss_30d": "net_loss_baseline_m"}


@app.get("/players/{player_id}", response_model=schemas.PlayerDetail, tags=["players"])
def get_player(player_id: str, recent: int = Query(25, ge=0, le=500)):
    """Profile, score, all computed features and the most recent transactions."""
    require_player(player_id)
    f = store.features.loc[player_id]
    s = store.scores.loc[player_id]
    a = store.alert_by_player.get(player_id)
    tx = store.player_transactions(player_id).tail(recent).iloc[::-1]
    return {
        "player_id": player_id,
        "profile": {k: f[k] for k in ["age_band", "occupation", "income_band", "home_region", "signup_date"]},
        "score": int(s["score"]), "band": s["band"], "team": s["team"] if isinstance(s["team"], str) else "",
        "alert_id": a["alert_id"] if a else None,
        "peer_group": f["peer_group"], "peer_group_size": int(f["peer_group_size"]),
        "monthly_income_estimate": float(f["monthly_income_estimate"]),
        "features": {k: clean(f[k]) for k in FEATURE_FIELDS},
        "recent_transactions": txn_records(tx),
    }


@app.get("/players/{player_id}/transactions", response_model=schemas.TransactionPage, tags=["players"])
def player_transactions(player_id: str, type: Optional[str] = Query(None, description="deposit, withdrawal, bet, payout"),
                        since: Optional[str] = Query(None, description="ISO date, inclusive"),
                        limit: int = Query(100, ge=1, le=2000), offset: int = Query(0, ge=0)):
    """Transaction history, newest first."""
    require_player(player_id)
    tx = store.player_transactions(player_id)
    if type:
        tx = tx[tx["type"].astype(str).isin([t.strip() for t in type.split(",")])]
    if since:
        tx = tx[tx["timestamp"] >= pd.Timestamp(since)]
    tx = tx.iloc[::-1]
    return {"total": len(tx), "limit": limit, "offset": offset, "items": txn_records(tx.iloc[offset: offset + limit])}


@app.get("/players/{player_id}/peers", response_model=schemas.PeerComparison, tags=["players"])
def player_peers(player_id: str):
    """Player value vs own baseline vs peer-group distribution, per feature (for the peer comparison chart)."""
    require_player(player_id)
    f = store.features.loc[player_id]
    group = f["peer_group"]
    out = []
    for feat, label in PEER_LABELS.items():
        try:
            st = store.peer_stats.loc[(group, feat)]
        except KeyError:
            st = None
        z = clean(f.get(f"z_{feat}"))
        out.append({
            "feature": feat, "label": label, "value": float(f[feat]),
            "own_baseline": clean(f[BASELINE_FOR[feat]]) if feat in BASELINE_FOR else None,
            "peer_median": clean(st["median"]) if st is not None else None,
            "peer_q1": clean(st["q1"]) if st is not None else None,
            "peer_q3": clean(st["q3"]) if st is not None else None,
            "peer_p90": clean(st["p90"]) if st is not None else None,
            "z_score": z, "percentile": clean(f.get(f"pct_{feat}")),
            "flagged": bool(z is not None and z >= WEIGHTS["z_threshold"]),
        })
    return {"player_id": player_id, "peer_group": group, "peer_group_size": int(f["peer_group_size"]),
            "z_threshold": WEIGHTS["z_threshold"], "features": out}


@app.get("/players/{player_id}/timeline", response_model=schemas.Timeline, tags=["players"])
def player_timeline(player_id: str):
    """Weekly activity series for the behaviour-over-time chart, tagged baseline / current window."""
    require_player(player_id)
    tx = store.player_transactions(player_id).copy()
    cur_start, base_start = store.window_starts
    ref = store.reference_date
    weeks = []
    if len(tx):
        tx["week"] = (tx["timestamp"] - pd.to_timedelta(tx["timestamp"].dt.weekday, unit="D")).dt.normalize()
        tx["type"] = tx["type"].astype(str)
        for wk, g in tx.groupby("week"):
            amt = g.groupby("type")["amount_cad"].sum()
            bets = g[g["type"] == "bet"]
            staked, payouts = float(amt.get("bet", 0)), float(amt.get("payout", 0))
            window = "current" if wk + pd.Timedelta(days=6) >= cur_start else ("baseline" if wk + pd.Timedelta(days=6) >= base_start else "earlier")
            weeks.append({
                "week_start": wk.date().isoformat(), "deposits": round(float(amt.get("deposit", 0)), 2),
                "withdrawals": round(float(amt.get("withdrawal", 0)), 2), "staked": round(staked, 2),
                "payouts": round(payouts, 2), "net_loss": round(staked - payouts, 2), "bets": int(len(bets)),
                "night_share": round(float((bets["timestamp"].dt.hour < 6).mean()), 3) if len(bets) else 0.0,
                "regions": sorted(g["ip_region"].astype(str).unique().tolist()), "window": window,
            })
    return {"player_id": player_id, "reference_date": ref.date().isoformat(), "current_start": cur_start.date().isoformat(),
            "baseline_start": base_start.date().isoformat(), "weeks": weeks}


@app.get("/players/{player_id}/network", response_model=schemas.Network, tags=["players"])
def player_network(player_id: str, hops: int = Query(2, ge=1, le=3)):
    """Players linked through shared devices, payment methods or addresses (up to `hops` steps away)."""
    require_player(player_id)
    return get_graph(store).neighbourhood(player_id, hops=hops)


@app.get("/network/clusters", tags=["players"])
def network_clusters(min_size: int = Query(3, ge=2)):
    """Connected groups of linked players, highest-risk first."""
    return get_graph(store).clusters(min_size=min_size)
