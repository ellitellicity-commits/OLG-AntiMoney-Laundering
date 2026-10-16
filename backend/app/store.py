"""Loads pipeline outputs into memory and keeps investigator decisions in SQLite.

Data directory defaults to <repo>/data and can be overridden with the OLG_DATA_DIR env var
(the tests use this to point at a small generated dataset).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path

import pandas as pd

from backend.pipeline.common import BASELINE_DAYS, CURRENT_DAYS, DATA_DIR


class DataNotReady(RuntimeError):
    pass


STATUS_FOR = {"accept": "accepted", "escalate": "escalated", "close": "closed"}


class DataStore:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir or os.environ.get("OLG_DATA_DIR") or DATA_DIR)
        self.synthetic = self.data_dir / "synthetic"
        self.features_dir = self.data_dir / "features"
        self.scores_dir = self.data_dir / "scores"
        self._lock = threading.Lock()
        self._init_db()

    # ---- files ----------------------------------------------------------------------
    def _need(self, path: Path) -> Path:
        if not path.exists():
            raise DataNotReady(f"{path.relative_to(self.data_dir.parent) if self.data_dir.parent in path.parents else path} "
                               "is missing. Run the pipeline first: python -m backend.pipeline.run_all")
        return path

    @cached_property
    def alerts(self) -> list[dict]:
        with open(self._need(self.scores_dir / "alerts.json"), encoding="utf-8") as fh:
            return json.load(fh)

    @cached_property
    def alerts_by_id(self) -> dict[str, dict]:
        return {a["alert_id"]: a for a in self.alerts}

    @cached_property
    def alert_by_player(self) -> dict[str, dict]:
        return {a["player_id"]: a for a in self.alerts}

    @cached_property
    def scores(self) -> pd.DataFrame:
        return pd.read_csv(self._need(self.scores_dir / "risk_scores.csv")).set_index("player_id", drop=False)

    @cached_property
    def features(self) -> pd.DataFrame:
        return pd.read_parquet(self._need(self.features_dir / "player_features.parquet")).set_index("player_id", drop=False)

    @cached_property
    def peer_stats(self) -> pd.DataFrame:
        return pd.read_parquet(self._need(self.features_dir / "peer_stats.parquet")).set_index(["peer_group", "feature"])

    @cached_property
    def transactions(self) -> pd.DataFrame:
        t = pd.read_parquet(self._need(self.features_dir / "transactions.parquet"))
        t["player_id"] = t["player_id"].astype(str)
        return t.sort_values(["player_id", "timestamp"]).reset_index(drop=True)

    @cached_property
    def txn_index(self) -> dict[str, tuple[int, int]]:
        """player_id -> (start, end) row slice into the player-sorted transactions frame."""
        pids = self.transactions["player_id"].to_numpy()
        idx, start = {}, 0
        for i in range(1, len(pids) + 1):
            if i == len(pids) or pids[i] != pids[start]:
                idx[pids[start]] = (start, i)
                start = i
        return idx

    @cached_property
    def linked(self) -> pd.DataFrame:
        return pd.read_csv(self._need(self.synthetic / "linked_identifiers.csv"))

    @cached_property
    def validation(self) -> dict:
        with open(self._need(self.scores_dir / "validation_report.json"), encoding="utf-8") as fh:
            return json.load(fh)

    @cached_property
    def reference_date(self) -> pd.Timestamp:
        return pd.Timestamp(self.features["reference_date"].iloc[0])

    @property
    def window_starts(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        cur = self.reference_date - pd.Timedelta(days=CURRENT_DAYS)
        return cur, cur - pd.Timedelta(days=BASELINE_DAYS)

    def player_transactions(self, pid: str) -> pd.DataFrame:
        a, b = self.txn_index.get(pid, (0, 0))
        return self.transactions.iloc[a:b]

    def warm(self):
        """Load everything up front so the first dashboard request is fast."""
        for name in ["alerts_by_id", "alert_by_player", "scores", "features", "peer_stats", "txn_index", "linked"]:
            getattr(self, name)

    # ---- decisions ------------------------------------------------------------------
    @property
    def db_path(self) -> Path:
        return self.data_dir / "decisions.db"

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, alert_id TEXT NOT NULL, decision TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '', reason TEXT, investigator TEXT, created_at TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS ix_decisions_alert ON decisions(alert_id, id)")

    def add_decision(self, alert_id: str, decision: str, note: str, reason: str | None, investigator: str | None) -> dict:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock, self._conn() as c:
            cur = c.execute("INSERT INTO decisions(alert_id, decision, note, reason, investigator, created_at) VALUES (?,?,?,?,?,?)",
                            (alert_id, decision, note, reason, investigator, now))
            new_id = cur.lastrowid
        return {"id": new_id, "alert_id": alert_id, "decision": decision, "note": note, "reason": reason,
                "investigator": investigator, "created_at": now, "status": STATUS_FOR[decision]}

    def decisions_for(self, alert_id: str) -> list[dict]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM decisions WHERE alert_id=? ORDER BY id", (alert_id,)).fetchall()
        return [dict(r) | {"status": STATUS_FOR[r["decision"]]} for r in rows]

    def latest_decisions(self) -> dict[str, dict]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("""SELECT d.* FROM decisions d JOIN (SELECT alert_id, MAX(id) mid FROM decisions GROUP BY alert_id) m
                                ON d.id = m.mid""").fetchall()
        return {r["alert_id"]: dict(r) for r in rows}

    def clear_decisions(self):
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM decisions")
