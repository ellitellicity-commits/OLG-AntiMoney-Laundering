# Jube Integration

[Jube](https://github.com/jube-home/jube) is open-source AML / fraud transaction monitoring with built-in case management.
This integration turns our high-risk alerts into **Jube cases** and brings investigators' case decisions **back** into our queue.

```
our pipeline ──alerts.json──▶ push ──POST /api/Invoke/EntityAnalysisModel/{guid}──▶ Jube model
                                                                                      │ activation rule
                                                                                      ▼ RiskScore >= 70
our decision store ◀── pull ◀──GET /api/GetCaseByCaseKeyValueQuery?key=PlayerId──── Jube case (one per player)
```

The code is in `backend/integrations/`. It uses only the Python standard library and does not depend on which backend you run:

| File | Purpose |
|---|---|
| `jube.py` | Client, alert-to-payload mapping, case-to-decision mapping, push / pull, CLI |
| `jube_router.py` | Optional FastAPI router (`/jube/status`, `/jube/spec`, `/jube/push`, `/jube/pull`) that any backend can mount |
| `jube_mock.py` | A small stand-in for Jube with the same endpoint paths, for demos and tests without Docker |

`normalise_alert` accepts the alert shape from either team backend and from the `frontend-mock` API contract (`score`/`risk_score`, `title`/`headline`, `points`/`weight`, `action`/`label`).

## Option A: demo with the mock (no Docker, 1 minute)

```powershell
# terminal 1: fake Jube
uvicorn backend.integrations.jube_mock:app --port 5001

# terminal 2: our API, pointed at it
$env:JUBE_URL="http://127.0.0.1:5001"; $env:JUBE_MODEL_GUID="00000000-0000-0000-0000-000000000001"
uvicorn backend.app.main:app --reload
```

Then:

1. `POST http://127.0.0.1:8000/jube/push`: alerts scoring 70+ become cases (246 on the default seed).
2. Play the investigator "in Jube": `POST http://127.0.0.1:5001/mock/cases/1/status?name=Escalated&user=analyst.a`. Statuses are `Open`, `In Review`, `Escalated` and `Closed`.
3. `POST http://127.0.0.1:8000/jube/pull`: the alert now shows status `Escalated` in the dashboard, and the audit trail shows `analyst.a (via Jube)`.

Be upfront in the demo that this is a mock of Jube's API, not Jube itself.

## Option B: real Jube

1. **Run Jube.** Clone https://github.com/jube-home/jube, export the five `DockerCompose*` keys its README lists (Postgres password, JWT key, API HMAC key, password-hashing key, element-encryption key), then run `docker compose up -d`. The UI is at https://localhost:5001 and the first login is `Administrator` / `Administrator` (you must change the password). It builds from source, so allow time and disk space.
2. **Create the model.** In Models, create an Entity Analysis Model named `OLG Sports Betting`, with the entity key `PlayerId`, transaction ID `TxnId` and date `TxnDateTime`.
3. **Add the Request XPath fields.** `python -m backend.integrations.jube spec` prints the list. Each is `$.<Name>`, with `PlayerId` as a search key. Types: `RiskScore` and `ReasonCount` are Integer; `Deposits30d`, `Withdrawals30d` and `NetLoss30d` are Float; everything else is String.
4. **Create the case workflow.** In Case Workflows, create `OLG Investigations` with the statuses `Open`, `In Review`, `Escalated` and `Closed`. The pull step maps status names containing *review*/*accept* to `accept` and *escalat* to `escalate`, and a Jube-closed case maps to `close`.
5. **Add the activation rule.** Create `OLGRiskScoreCase` with the condition `RiskScore >= 70`. Tick **Cases**, then set Case Workflow = `OLG Investigations`, status = `Open` and **Case Key = `PlayerId`**. Jube then keeps one open case per player.
6. **Synchronise.** Run Entity » Synchronisation, then copy the model's GUID.
7. **Create an API key** for a user whose role can see Cases. Jube recommends API keys for integrations: they don't expire, unlike its 15-minute JWTs.
8. **Configure.** Put these in `.env` in the repo root (it is git-ignored):

   ```
   JUBE_URL=https://localhost:5001
   JUBE_MODEL_GUID=<model guid>
   JUBE_API_KEY=<api key>
   JUBE_VERIFY_TLS=false        # Jube's dev certificate is self-signed
   ```

9. **Check.** Run `python -m backend.integrations.jube status`, then `push --dry-run`, then `push`, and open Cases in Jube.

If the model's Invoke endpoint is exposed publicly (`EnablePublicInvokeController=true`), the push works without a key. Pulling cases always needs a key or a token.

## CLI

```bash
python -m backend.integrations.jube status            # config + reachability + sync counts
python -m backend.integrations.jube spec              # fields and rule to configure in Jube
python -m backend.integrations.jube push --dry-run    # show payloads, send nothing
python -m backend.integrations.jube push [--min-score 70] [--force] [--alerts path/to/alerts.json]
python -m backend.integrations.jube pull              # print decisions found in Jube
```

Sync state (which alerts have been sent, and which decisions were already pulled) is kept in `data/jube_sync.json`, which is git-ignored. An alert is re-sent only when its score changes, or with `--force`.

## How it is wired into the API

`backend/app/main.py` mounts the router with two small adapters:

- `jube_alerts()` passes `store.alerts`, adds the current team (after any reassignment) and the 30-day money figures from `player_features.parquet` (`deposits_30d`, `withdrawals_30d`, `turnover_30d`, `net_loss_30d`).
- `jube_decision()` stores a pulled decision through `store.save_decision`, exactly like a dashboard decision. The investigator is recorded as `<jube user> (via Jube)`, so it shows in `/audit`. Jube statuses map onto dashboard statuses through `STATUS_FOR`: accept → In review, escalate → Escalated, close → Closed.

Another FastAPI app can mount the same router:

```python
from backend.integrations.jube_router import make_jube_router
app.include_router(make_jube_router(get_alerts=lambda: ALERTS, record_decision=save_decision))
```

## What's verified, and what isn't

- **Verified against Jube's source code** (`Jube.App/Endpoints`, `Jube.Dto`): the invoke path; the `X-API-KEY` and bearer authentication; the `GetCaseByCaseKeyValueQuery` and `PUT /api/Case` routes; the case fields (`ClosedStatusId` 0 = open … 3 = closed, `CaseWorkflowStatusName`, `LockedUser`); and the round-trip date format.
- **Tested** against `jube_mock.py` over real HTTP: `tests/test_jube.py` (11 tests: mapping, bad keys, a wrong model GUID, an unreachable server, duplicate pushes) and `tests/test_jube_app.py` (the push → escalate in Jube → pull round trip through the real API and audit trail).
- **Not tested against a running Jube instance.** The shape of the invoke response varies with each model's Response Payload settings, so the client stores it as-is and doesn't depend on it.
