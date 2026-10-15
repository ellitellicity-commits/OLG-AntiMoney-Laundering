"""A tiny stand-in for Jube, for demos and tests when the real Jube (Docker, Postgres, Redis) isn't running.

It implements only the endpoints `jube.py` uses, with the same paths and field names as Jube:
    POST /api/Invoke/EntityAnalysisModel/{guid}     archive the event; open a case when RiskScore >= threshold
    GET  /api/GetCaseByCaseKeyValueQuery?key=&value= cases for one case key value
    PUT  /api/Case                                  update status (CaseWorkflowStatusGuid / ClosedStatusId)
    POST /api/Authentication/Logout                 reachability check
Plus mock-only helpers to play the investigator inside "Jube":
    GET  /mock/cases                                list every case
    POST /mock/cases/{id}/status?name=Escalated     move a case to a workflow status (Closed closes it)

Run:   uvicorn backend.integrations.jube_mock:app --port 5001
Then:  JUBE_URL=http://127.0.0.1:5001  JUBE_MODEL_GUID=00000000-0000-0000-0000-000000000001
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Request

MODEL_GUID = os.environ.get("JUBE_MOCK_MODEL_GUID", "00000000-0000-0000-0000-000000000001")
API_KEY = os.environ.get("JUBE_MOCK_API_KEY", "")  # when set, requests must send this X-API-KEY
THRESHOLD = int(os.environ.get("JUBE_MOCK_THRESHOLD", "70"))
CASE_KEY = "PlayerId"
WORKFLOW_GUID = "11111111-1111-1111-1111-111111111111"
STATUSES = {name: str(uuid.uuid5(uuid.NAMESPACE_URL, f"jube-mock/{name}"))
            for name in ["Open", "In Review", "Escalated", "Closed"]}
STATUS_BY_GUID = {g: n for n, g in STATUSES.items()}

app = FastAPI(title="Jube (mock)", description="Minimal Jube stand-in for the OLG AML demo. Not the real Jube.")
DB: dict[str, Any] = {"events": [], "cases": {}, "next_id": 1}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_key(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Invalid or missing X-API-KEY")


def reset():
    DB.update(events=[], cases={}, next_id=1)


@app.post("/api/Invoke/EntityAnalysisModel/{guid}")
async def invoke(guid: str, request: Request, x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    if guid != MODEL_GUID:
        raise HTTPException(404, "Model not found")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Body must be JSON") from None
    entry = str(uuid.uuid4())
    DB["events"].append({"guid": entry, "payload": payload, "received": now()})
    activation = {}
    score = int(payload.get("RiskScore", 0) or 0)
    key_value = str(payload.get(CASE_KEY, ""))
    if score >= THRESHOLD and key_value:
        activation["OLGRiskScoreCase"] = {"Visible": 1}
        open_case = next((c for c in DB["cases"].values()
                          if c["CaseKeyValue"] == key_value and c["ClosedStatusId"] == 0), None)
        if open_case is None:  # Jube enforces one open case per Case Key Value per workflow
            cid = DB["next_id"]
            DB["next_id"] += 1
            DB["cases"][cid] = {
                "Id": cid, "EntityAnalysisModelInstanceEntryGuid": entry, "CaseWorkflowGuid": WORKFLOW_GUID,
                "CaseWorkflowStatusGuid": STATUSES["Open"], "CaseWorkflowStatusName": "Open",
                "CreatedDate": now(), "Locked": False, "LockedUser": "", "ClosedStatusId": 0, "ClosedUser": "",
                "CaseKey": CASE_KEY, "CaseKeyValue": key_value, "Rating": 0, "Json": payload,
            }
            activation["OLGRiskScoreCase"]["CaseId"] = cid
    return {"EntityAnalysisModelInstanceEntryGuid": entry, "EntityInstanceEntryId": payload.get("TxnId"),
            "Activation": activation, "ResponseElevation": {"Value": score}}


@app.get("/api/GetCaseByCaseKeyValueQuery")
def cases_by_key(key: str, value: str, x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    return [{k: v for k, v in c.items() if k != "Json"} for c in DB["cases"].values()
            if c["CaseKey"] == key and c["CaseKeyValue"] == value]


@app.put("/api/Case")
async def update_case(request: Request, x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    body = await request.json()
    case = DB["cases"].get(int(body.get("Id", 0)))
    if not case:
        raise HTTPException(404, "Case not found")
    if body.get("CaseWorkflowStatusGuid") in STATUS_BY_GUID:
        case["CaseWorkflowStatusGuid"] = body["CaseWorkflowStatusGuid"]
        case["CaseWorkflowStatusName"] = STATUS_BY_GUID[body["CaseWorkflowStatusGuid"]]
    for k in ("Locked", "LockedUser", "ClosedStatusId", "Rating"):
        if k in body:
            case[k] = body[k]
    return {}


@app.post("/api/Authentication/Logout")
def logout():
    return {}


@app.get("/mock/cases")
def list_cases():
    return [{k: v for k, v in c.items() if k != "Json"} for c in DB["cases"].values()]


@app.post("/mock/cases/{case_id}/status")
def set_status(case_id: int, name: str, user: str = "jube.investigator"):
    case = DB["cases"].get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    if name not in STATUSES:
        raise HTTPException(400, f"status must be one of {list(STATUSES)}")
    case.update(CaseWorkflowStatusName=name, CaseWorkflowStatusGuid=STATUSES[name], Locked=name != "Open",
                LockedUser=user if name != "Open" else "")
    if name == "Closed":
        case.update(ClosedStatusId=3, ClosedUser=user, ClosedDate=now())
    return {k: v for k, v in case.items() if k != "Json"}


@app.post("/mock/reset")
def mock_reset():
    reset()
    return {"ok": True}
