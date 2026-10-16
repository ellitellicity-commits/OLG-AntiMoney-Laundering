"""Optional FastAPI router so any backend can expose Jube sync to the dashboard.

Usage in a FastAPI app:
    from backend.integrations.jube_router import make_jube_router
    app.include_router(make_jube_router(get_alerts=lambda: store.alerts,
                                        record_decision=lambda alert_id, d: store.add_decision(alert_id, **d)))

`get_alerts()` returns the backend's alert dicts (any shape `jube.normalise_alert` understands).
`record_decision(alert_id, {"decision", "note", "reason", "investigator"})` stores a decision pulled from Jube.

Endpoints: GET /jube/status, GET /jube/spec, POST /jube/push, POST /jube/pull
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.integrations import jube


def make_jube_router(get_alerts: Callable[[], list[dict]],
                     record_decision: Optional[Callable[[str, dict], Any]] = None,
                     client_factory: Callable[[], jube.JubeClient] = jube.JubeClient) -> APIRouter:
    router = APIRouter(prefix="/jube", tags=["jube"])

    def client() -> jube.JubeClient:
        c = client_factory()
        if not c.cfg.configured:
            raise HTTPException(503, "Jube is not configured: set JUBE_URL and JUBE_MODEL_GUID (see docs/JUBE.md)")
        return c

    @router.get("/status")
    def status():
        """Configuration, reachability and how many alerts have been synced."""
        return jube.status(client_factory())

    @router.get("/spec")
    def spec():
        """The Request XPath fields and activation rule to configure in the Jube model."""
        return jube.model_spec(client_factory().cfg)

    @router.post("/push")
    def push(min_score: Optional[int] = Query(None, ge=0, le=100), dry_run: bool = False, force: bool = False):
        """Send alerts at or above the threshold to Jube, where an activation rule opens one case per player."""
        res = jube.push_alerts(get_alerts(), client(), min_score=min_score, dry_run=dry_run, force=force)
        return {"summary": _count(res), "results": [{k: v for k, v in r.items() if k != "response"} for r in res]}

    @router.post("/pull")
    def pull():
        """Read case statuses from Jube and record new accept / escalate / close decisions."""
        res = jube.pull_decisions(get_alerts(), client(), record=record_decision)
        return {"summary": _count(res), "results": res}

    return router


def _count(results: list[dict]) -> dict:
    out: dict[str, int] = {}
    for r in results:
        out[r["status"]] = out.get(r["status"], 0) + 1
    return out
