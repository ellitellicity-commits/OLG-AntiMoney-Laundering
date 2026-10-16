"""Jube integration: push risk alerts to Jube as cases and pull investigator decisions back.

Standalone on purpose: standard library only, and it works with any alert dict that has a player ID,
a score and a list of reasons, so either team backend can use it. Field names are normalised
in `normalise_alert`.

How it maps onto Jube (https://github.com/jube-home/jube):
    push  ->  POST {JUBE_URL}/api/Invoke/EntityAnalysisModel/{JUBE_MODEL_GUID}
              One flat JSON payload per alert. A Jube activation rule (e.g. RiskScore >= 70) with
              "Cases" enabled and Case Key = PlayerId opens one case per player in a case workflow.
    pull  ->  GET  {JUBE_URL}/api/GetCaseByCaseKeyValueQuery?key=PlayerId&value=<player_id>
              The case status is mapped back to accept / escalate / close (see `case_to_decision`).
    auth  ->  X-API-KEY header (Jube's recommended integration auth) or a bearer JWT, from env.

Configuration (environment variables, or a .env file in the repo root):
    JUBE_URL            default https://localhost:5001
    JUBE_MODEL_GUID     the Entity Analysis Model's GUID (Jube UI: Models -> the model -> Guid)
    JUBE_API_KEY        API key (preferred)  |  JUBE_TOKEN  a JWT  |  JUBE_USERNAME + JUBE_PASSWORD
    JUBE_VERIFY_TLS     "false" to accept Jube's self-signed dev certificate (default true)
    JUBE_MIN_SCORE      only alerts at or above this score are pushed (default 70)
    JUBE_CASE_KEY       payload field cases are keyed on (default PlayerId)
    JUBE_TIMEOUT        seconds (default 10)

CLI (from the repo root):
    python -m backend.integrations.jube status
    python -m backend.integrations.jube spec                      # Jube model fields to configure
    python -m backend.integrations.jube push [--dry-run] [--min-score 70] [--alerts data/scores/alerts.json]
    python -m backend.integrations.jube pull [--alerts ...]
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALERTS = ROOT / "data" / "scores" / "alerts.json"
DEFAULT_STATE = ROOT / "data" / "jube_sync.json"

# Jube Case.ClosedStatusId codes (Jube.Dto.Repository.Case.CaseDto)
CLOSED_STATUS = {0: "open", 1: "suspended", 2: "reopened", 3: "closed", 4: "bypassed"}


# --------------------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------------------
def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader (KEY=VALUE lines); never overrides variables already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@dataclass
class JubeConfig:
    url: str = "https://localhost:5001"
    model_guid: str = ""
    api_key: str = ""
    token: str = ""
    username: str = ""
    password: str = ""
    verify_tls: bool = True
    min_score: int = 70
    case_key: str = "PlayerId"
    timeout: float = 10.0

    @classmethod
    def from_env(cls) -> "JubeConfig":
        load_dotenv()
        e = os.environ.get
        return cls(
            url=e("JUBE_URL", cls.url).rstrip("/"),
            model_guid=e("JUBE_MODEL_GUID", ""),
            api_key=e("JUBE_API_KEY", ""),
            token=e("JUBE_TOKEN", ""),
            username=e("JUBE_USERNAME", ""),
            password=e("JUBE_PASSWORD", ""),
            verify_tls=e("JUBE_VERIFY_TLS", "true").lower() not in ("0", "false", "no"),
            min_score=int(e("JUBE_MIN_SCORE", cls.min_score)),
            case_key=e("JUBE_CASE_KEY", cls.case_key),
            timeout=float(e("JUBE_TIMEOUT", cls.timeout)),
        )

    @property
    def configured(self) -> bool:
        return bool(self.url and self.model_guid)


class JubeError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


# --------------------------------------------------------------------------------------
# alert -> Jube payload
# --------------------------------------------------------------------------------------
def _first(d: dict, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def normalise_alert(alert: dict) -> dict:
    """Accept either team backend's alert shape (or the frontend API contract) and return one shape.

    Handles score/risk_score, title/headline, detail/evidence-as-text, points/weight,
    recommended_action.action/label, and anomaly_type/type on reasons.
    """
    rec = alert.get("recommended_action") or {}
    if isinstance(rec, str):
        rec = {"action": rec}
    reasons = []
    for r in alert.get("reasons") or []:
        ev = r.get("evidence")
        reasons.append({
            "code": _first(r, "code", "type", default=""),
            "type": _first(r, "anomaly_type", "type", default=""),
            "title": _first(r, "title", "headline", default=""),
            "detail": _first(r, "detail", default=ev if isinstance(ev, str) else ""),
            "points": int(_first(r, "points", "weight", default=0) or 0),
        })
    pid = str(_first(alert, "player_id", "playerId", default=""))
    return {
        "player_id": pid,
        "alert_id": str(_first(alert, "alert_id", "id", default=f"A-{pid}")),
        "score": int(_first(alert, "score", "risk_score", default=0) or 0),
        "band": str(_first(alert, "band", default="")),
        "team": str(_first(alert, "team", default=rec.get("team", "")) or ""),
        "anomaly_types": list(alert.get("anomaly_types") or []),
        "reasons": reasons,
        "action": str(_first(rec, "action", "label", default="")),
        "action_team": str(rec.get("team", "")),
        "rationale": str(rec.get("rationale", "")),
        "summary": str(_first(alert, "summary", default="")),
        "created_at": str(_first(alert, "created_at", "as_of", default="")),
        "key_metrics": alert.get("key_metrics") or {},
        "profile": alert.get("profile") or {},
    }


def jube_datetime(value: str | None = None) -> str:
    """Jube parses dates with .NET round-trip format, e.g. 2026-10-01T00:00:00.0000000+00:00."""
    if value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f0") + dt.strftime("%z")[:3] + ":" + dt.strftime("%z")[3:]


def alert_to_payload(alert: dict, sent_at: str | None = None) -> dict:
    """Flat JSON for Jube's invoke endpoint. Every field listed in JUBE_FIELDS is a JSONPath Jube can read."""
    a = normalise_alert(alert)
    km = a["key_metrics"]
    p = a["profile"]
    top = a["reasons"][0] if a["reasons"] else {}
    return {
        "PlayerId": a["player_id"],
        "AlertId": a["alert_id"],
        # TxnId must be unique per invocation; re-pushing a rescored alert creates a new archived event
        "TxnId": f"{a['alert_id']}-{a['score']}-{(sent_at or jube_datetime())[:19].replace(':', '')}",
        "TxnDateTime": jube_datetime(a["created_at"] or None),
        "RiskScore": a["score"],
        "Band": a["band"],
        "Team": a["team"],
        "AnomalyTypes": ";".join(a["anomaly_types"]),
        "PrimaryAnomalyType": top.get("type", ""),
        "TopReasonCode": top.get("code", ""),
        "TopReasonTitle": top.get("title", ""),
        "ReasonCount": len(a["reasons"]),
        "RecommendedAction": a["action"],
        "Rationale": a["rationale"],
        "Summary": a["summary"],
        "CurrencyAmount": float(km.get("deposits_30d", 0) or 0),
        "Deposits30d": float(km.get("deposits_30d", 0) or 0),
        "Withdrawals30d": float(km.get("withdrawals_30d", 0) or 0),
        "NetLoss30d": float(km.get("net_loss_30d", 0) or 0),
        "IncomeBand": str(p.get("income_band", "")),
        "Occupation": str(p.get("occupation", "")),
        "HomeRegion": str(p.get("home_region", "")),
        "Reasons": [{"Code": r["code"], "Type": r["type"], "Title": r["title"], "Detail": r["detail"],
                     "Points": r["points"]} for r in a["reasons"]],
        "Source": "OLG-AML synthetic data",
    }


# name, JSONPath, Jube data type, search key?  (configure these as Request XPath in the Jube model)
JUBE_FIELDS = [
    ("PlayerId", "$.PlayerId", "String", True),
    ("AlertId", "$.AlertId", "String", False),
    ("RiskScore", "$.RiskScore", "Integer", False),
    ("Band", "$.Band", "String", False),
    ("Team", "$.Team", "String", False),
    ("AnomalyTypes", "$.AnomalyTypes", "String", False),
    ("PrimaryAnomalyType", "$.PrimaryAnomalyType", "String", False),
    ("TopReasonCode", "$.TopReasonCode", "String", False),
    ("TopReasonTitle", "$.TopReasonTitle", "String", False),
    ("ReasonCount", "$.ReasonCount", "Integer", False),
    ("RecommendedAction", "$.RecommendedAction", "String", False),
    ("Summary", "$.Summary", "String", False),
    ("Deposits30d", "$.Deposits30d", "Float", False),
    ("Withdrawals30d", "$.Withdrawals30d", "Float", False),
    ("NetLoss30d", "$.NetLoss30d", "Float", False),
    ("IncomeBand", "$.IncomeBand", "String", False),
    ("Occupation", "$.Occupation", "String", False),
    ("HomeRegion", "$.HomeRegion", "String", False),
]


def model_spec(cfg: JubeConfig | None = None) -> dict:
    cfg = cfg or JubeConfig.from_env()
    return {
        "request_xpath": [{"name": n, "xpath": x, "data_type": t, "search_key": s} for n, x, t, s in JUBE_FIELDS],
        "activation_rule": {
            "name": "OLGRiskScoreCase",
            "condition": f"RiskScore >= {cfg.min_score}",
            "cases": True, "case_key": cfg.case_key,
        },
        "case_workflow_statuses": ["Open", "In Review", "Escalated", "Closed"],
        "notes": "Model entry/date fields: entity = PlayerId, transaction id = TxnId, date = TxnDateTime.",
    }


# --------------------------------------------------------------------------------------
# Jube case -> our decision
# --------------------------------------------------------------------------------------
def case_to_decision(case: dict) -> dict | None:
    """Map a Jube case (CaseByCaseKeyValueDto) to an accept / escalate / close decision, or None if untouched.

    Precedence: closed in Jube -> close; a workflow status named like 'escalat' -> escalate;
    a status like 'review'/'accept' or a locked case (someone picked it up) -> accept.
    """
    closed = CLOSED_STATUS.get(int(case.get("ClosedStatusId", case.get("closedStatusId", 0)) or 0), "open")
    status = str(case.get("CaseWorkflowStatusName", case.get("caseWorkflowStatusName", "")) or "")
    s = status.lower()
    user = case.get("ClosedUser") or case.get("closedUser") or case.get("LockedUser") or case.get("lockedUser") or "jube"
    note = f"Jube case {case.get('Id', case.get('id', '?'))}: status '{status or closed}'"
    if closed == "closed":
        return {"decision": "close", "reason": f"Closed in Jube ({status or 'closed'})", "note": note, "investigator": user}
    if "escalat" in s:
        return {"decision": "escalate", "reason": None, "note": note, "investigator": user}
    if "review" in s or "accept" in s or case.get("Locked") or case.get("locked"):
        return {"decision": "accept", "reason": None, "note": note, "investigator": user}
    return None


# --------------------------------------------------------------------------------------
# HTTP client
# --------------------------------------------------------------------------------------
class JubeClient:
    def __init__(self, cfg: JubeConfig | None = None):
        self.cfg = cfg or JubeConfig.from_env()
        self._ctx = None if self.cfg.verify_tls else ssl._create_unverified_context()  # dev cert only
        self._jwt = self.cfg.token

    # -- low level ---------------------------------------------------------------------
    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.cfg.api_key:
            h["X-API-KEY"] = self.cfg.api_key
        elif self._jwt:
            h["Authorization"] = f"Bearer {self._jwt}"
        return h

    def request(self, method: str, path: str, body: Any = None, params: dict | None = None, auth: bool = True) -> Any:
        url = f"{self.cfg.url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        if auth and not self.cfg.api_key and not self._jwt and self.cfg.username:
            self.login()
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers=self._headers() if auth else {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout, context=self._ctx) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:500]
            hint = {401: "check JUBE_API_KEY / credentials", 403: "the key's role lacks permission for this page",
                    404: "check JUBE_MODEL_GUID and that the model is synchronised (Entity -> Synchronisation)",
                    503: "Jube engine not started yet"}.get(e.code, "")
            raise JubeError(f"Jube {method} {path} -> HTTP {e.code}" + (f" ({hint})" if hint else ""), e.code, text) from None
        except urllib.error.URLError as e:
            raise JubeError(f"Cannot reach Jube at {self.cfg.url}: {e.reason}") from None

    def login(self) -> str:
        """Trade username/password for a 15-minute JWT. Prefer an API key for integration."""
        out = self.request("POST", "/api/Authentication/ByUserNamePassword",
                           {"UserName": self.cfg.username, "Password": self.cfg.password}, auth=False)
        token = (out or {}).get("token") or (out or {}).get("Token")
        if not token:
            raise JubeError("Jube login returned no token (password change pending? use an API key instead)")
        self._jwt = token
        return token

    # -- operations --------------------------------------------------------------------
    def invoke(self, payload: dict) -> Any:
        if not self.cfg.model_guid:
            raise JubeError("JUBE_MODEL_GUID is not set")
        return self.request("POST", f"/api/Invoke/EntityAnalysisModel/{self.cfg.model_guid}", payload)

    def cases_for(self, key_value: str, key: str | None = None) -> list[dict]:
        out = self.request("GET", "/api/GetCaseByCaseKeyValueQuery",
                           params={"key": key or self.cfg.case_key, "value": key_value})
        return out or []

    def update_case(self, case: dict) -> Any:
        return self.request("PUT", "/api/Case", case)

    def ping(self) -> dict:
        """Reachability check that needs no model: the anonymous Logout endpoint returns quickly."""
        try:
            self.request("POST", "/api/Authentication/Logout", {}, auth=False)
            return {"reachable": True}
        except JubeError as e:
            return {"reachable": e.status is not None, "detail": str(e)}


# --------------------------------------------------------------------------------------
# sync state + high-level operations
# --------------------------------------------------------------------------------------
@dataclass
class SyncState:
    path: Path = DEFAULT_STATE
    pushed: dict = field(default_factory=dict)   # alert_id -> {score, sent_at, txn_id}
    pulled: dict = field(default_factory=dict)   # alert_id -> last decision signature

    @classmethod
    def load(cls, path: Path | None = None) -> "SyncState":
        path = Path(path or os.environ.get("JUBE_STATE_PATH") or DEFAULT_STATE)
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            return cls(path, d.get("pushed", {}), d.get("pulled", {}))
        return cls(path)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"pushed": self.pushed, "pulled": self.pulled}, indent=1), encoding="utf-8")


def push_alerts(alerts: Iterable[dict], client: JubeClient | None = None, min_score: int | None = None,
                dry_run: bool = False, force: bool = False, state: SyncState | None = None) -> list[dict]:
    """Send alerts at or above min_score to Jube. Alerts already sent with the same score are skipped."""
    client = client or JubeClient()
    min_score = client.cfg.min_score if min_score is None else min_score
    state = state or SyncState.load()
    results = []
    for raw in alerts:
        a = normalise_alert(raw)
        if a["score"] < min_score:
            continue
        prev = state.pushed.get(a["alert_id"])
        if prev and prev.get("score") == a["score"] and not force:
            results.append({"alert_id": a["alert_id"], "status": "skipped", "detail": "already sent at this score"})
            continue
        sent_at = jube_datetime()
        payload = alert_to_payload(raw, sent_at)
        if dry_run:
            results.append({"alert_id": a["alert_id"], "status": "dry_run", "payload": payload})
            continue
        try:
            resp = client.invoke(payload)
            state.pushed[a["alert_id"]] = {"score": a["score"], "sent_at": sent_at, "txn_id": payload["TxnId"]}
            results.append({"alert_id": a["alert_id"], "status": "sent", "response": resp})
        except JubeError as e:
            results.append({"alert_id": a["alert_id"], "status": "error", "detail": str(e)})
            if e.status is None:  # Jube unreachable: stop instead of failing every alert
                break
    if not dry_run:
        state.save()
    return results


def pull_decisions(alerts: Iterable[dict], client: JubeClient | None = None,
                   record: Callable[[str, dict], Any] | None = None, state: SyncState | None = None,
                   only_pushed: bool = True) -> list[dict]:
    """Read each pushed alert's Jube case and turn status changes into decisions.

    `record(alert_id, decision)` is called for every new decision, so any backend can store it in its
    own decision store. Unchanged cases are not re-recorded.
    """
    client = client or JubeClient()
    state = state or SyncState.load()
    out = []
    for raw in alerts:
        a = normalise_alert(raw)
        if only_pushed and a["alert_id"] not in state.pushed:
            continue
        try:
            cases = client.cases_for(a["player_id"])
        except JubeError as e:
            out.append({"alert_id": a["alert_id"], "status": "error", "detail": str(e)})
            if e.status is None:
                break
            continue
        if not cases:
            out.append({"alert_id": a["alert_id"], "status": "no_case"})
            continue
        case = max(cases, key=lambda c: c.get("Id", c.get("id", 0)))  # newest case for the player
        decision = case_to_decision(case)
        if not decision:
            out.append({"alert_id": a["alert_id"], "status": "open_in_jube", "case_id": case.get("Id", case.get("id"))})
            continue
        sig = f"{decision['decision']}|{decision['note']}"
        if state.pulled.get(a["alert_id"]) == sig:
            out.append({"alert_id": a["alert_id"], "status": "unchanged", "decision": decision["decision"]})
            continue
        if record:
            record(a["alert_id"], decision)
        state.pulled[a["alert_id"]] = sig
        out.append({"alert_id": a["alert_id"], "status": "recorded", "decision": decision["decision"],
                    "case_id": case.get("Id", case.get("id"))})
    state.save()
    return out


def status(client: JubeClient | None = None) -> dict:
    client = client or JubeClient()
    c = client.cfg
    st = SyncState.load()
    auth = "api_key" if c.api_key else ("jwt" if c.token else ("password" if c.username else "none"))
    info = {"url": c.url, "model_guid_set": bool(c.model_guid), "auth": auth, "min_score": c.min_score,
            "case_key": c.case_key, "pushed": len(st.pushed), "decisions_pulled": len(st.pulled)}
    info.update(client.ping())
    return info


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def _load_alerts(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("alerts", data.get("items", data)) if isinstance(data, dict) else data


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sync OLG risk alerts with Jube case management.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="show configuration and whether Jube is reachable")
    sub.add_parser("spec", help="print the Jube model fields and activation rule to configure")
    p = sub.add_parser("push", help="send alerts to Jube")
    p.add_argument("--alerts", type=Path, default=DEFAULT_ALERTS)
    p.add_argument("--min-score", type=int)
    p.add_argument("--dry-run", action="store_true", help="print payloads without sending")
    p.add_argument("--force", action="store_true", help="resend alerts already sent at the same score")
    q = sub.add_parser("pull", help="read case statuses from Jube and print resulting decisions")
    q.add_argument("--alerts", type=Path, default=DEFAULT_ALERTS)
    args = ap.parse_args(argv)

    if args.cmd == "status":
        print(json.dumps(status(), indent=1))
    elif args.cmd == "spec":
        print(json.dumps(model_spec(), indent=1))
    elif args.cmd == "push":
        res = push_alerts(_load_alerts(args.alerts), min_score=args.min_score, dry_run=args.dry_run, force=args.force)
        if args.dry_run:
            print(json.dumps([r["payload"] for r in res[:2]], indent=1))
        counts: dict[str, int] = {}
        for r in res:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(json.dumps(counts))
        for r in res:
            if r["status"] == "error":
                print(f"  {r['alert_id']}: {r['detail']}", file=sys.stderr)
    elif args.cmd == "pull":
        res = pull_decisions(_load_alerts(args.alerts),
                             record=lambda aid, d: print(f"  {aid}: {d['decision']} ({d['note']})"))
        counts = {}
        for r in res:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(json.dumps(counts))


if __name__ == "__main__":
    main()
