"""Write frontend/mock/alerts.json: five real pipeline alerts (one per primary anomaly type) in the
same shape as GET /alerts/{alert_id}, so the dashboard can be built without the API running.

Usage:  python backend/pipeline/export_mock.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, SCORES_DIR  # noqa: E402

SHOWCASE_TYPES = ["income_mismatch", "location_anomaly", "behaviour_change", "linked_players", "peer_deviation"]


def pick_showcase(alerts: list[dict]) -> list[dict]:
    """Highest-ranked alert whose primary anomaly type is each showcase type."""
    picked = []
    for t in SHOWCASE_TYPES:
        a = next((a for a in alerts if a["recommended_action"].get("primary_type") == t), None)
        if a:
            picked.append(a)
    return picked


def main():
    alerts = json.loads((SCORES_DIR / "alerts.json").read_text(encoding="utf-8"))
    mock = [{**a, "status": "open", "latest_decision": None} for a in pick_showcase(alerts)]
    out = ROOT / "frontend" / "mock" / "alerts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(mock, indent=1), encoding="utf-8")
    for a in mock:
        print(f"{a['alert_id']}  {a['score']:>3} {a['band']:<8} {a['team']:<15} {a['top_reason_code']}")
    print(f"written to {out}")


if __name__ == "__main__":
    main()
