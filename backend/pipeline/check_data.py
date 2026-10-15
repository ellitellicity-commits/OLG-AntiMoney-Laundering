"""Check a dataset against the data contract before running the pipeline on it.

The pipeline was built on synthetic data, but every step reads plain files with the
columns below. Point this at an export from a real system (OLG account, payments,
KYC and device data, mapped to these columns) and it reports what is missing or
malformed. See docs/DATA_INTEGRATION.md for where each field would come from.

Usage:  python backend/pipeline/check_data.py [--dir path/to/folder]
        (default: data/synthetic; exits with code 1 if anything fails)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from common import HOME_REGIONS, INCOME_BANDS, JURISDICTION, OCCUPATION_INCOME, SYNTH, AGE_BANDS

CONTRACT = {
    "players.csv": {
        "player_id": "id", "age_band": AGE_BANDS, "occupation": "text", "income_band": INCOME_BANDS,
        "home_region": HOME_REGIONS, "signup_date": "date", "kyc_status": ["verified", "pending", "expired"],
        "pep": "bool", "sanctions_screening": ["clear", "potential match"],
    },
    "transactions.csv": {
        "txn_id": "id", "player_id": "id", "timestamp": "datetime",
        "type": ["deposit", "withdrawal", "bet", "payout"], "amount_cad": "amount",
        "sport": "text?", "market": "text?", "odds": "number?", "channel": ["app", "web", "retail"],
        "device_id": "text?", "ip_region": "text?", "payment_method_id": "text?",
    },
    "linked_identifiers.csv": {"player_id": "id", "identifier_type": ["device", "payment_method", "address"],
                               "identifier_value": "id"},
    "payment_methods.csv": {"payment_method_id": "id", "player_id": "id",
                            "method_type": ["debit card", "credit card", "bank transfer", "e-wallet"],
                            "holder_matches_player": "bool", "first_used": "date"},
}
MIN_DAYS = 120  # 30-day current window + 90-day baseline


class Report:
    def __init__(self):
        self.fails, self.warns = 0, 0

    def ok(self, msg):
        print(f"  OK    {msg}")

    def warn(self, msg):
        self.warns += 1
        print(f"  WARN  {msg}")

    def fail(self, msg):
        self.fails += 1
        print(f"  FAIL  {msg}")


def check_column(rep: Report, df: pd.DataFrame, name: str, kind) -> None:
    s = df[name]
    optional = isinstance(kind, str) and kind.endswith("?")
    kind = kind.rstrip("?") if isinstance(kind, str) else kind
    missing = s.isna() | (s.astype(str).str.strip() == "")
    if missing.any() and not optional:
        rep.fail(f"{name}: {int(missing.sum())} empty values")
    v = s[~missing]
    if isinstance(kind, list):
        bad = sorted(set(v.astype(str)) - {str(x) for x in kind})
        (rep.fail if bad else rep.ok)(f"{name}: " + (f"unexpected values {bad[:5]}" if bad else "values allowed"))
    elif kind in ("date", "datetime"):
        bad = pd.to_datetime(v, errors="coerce").isna().sum()
        (rep.fail if bad else rep.ok)(f"{name}: " + (f"{bad} unparseable dates" if bad else "dates parse"))
    elif kind in ("amount", "number"):
        num = pd.to_numeric(v, errors="coerce")
        bad = int(num.isna().sum() + (num < 0).sum())
        (rep.fail if bad else rep.ok)(f"{name}: " + (f"{bad} non-numeric or negative" if bad else "numeric"))
    elif kind == "bool":
        bad = sorted(set(v.astype(str).str.lower()) - {"true", "false", "1", "0"})
        (rep.fail if bad else rep.ok)(f"{name}: " + (f"not true/false: {bad[:5]}" if bad else "true/false"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", type=Path, default=SYNTH)
    folder = ap.parse_args().dir
    rep = Report()
    frames = {}
    print(f"Checking {folder}")
    for fname, cols in CONTRACT.items():
        print(f"\n{fname}")
        path = folder / fname
        if not path.exists():
            rep.fail("file missing")
            continue
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        frames[fname] = df
        absent = [c for c in cols if c not in df.columns]
        if absent:
            rep.fail(f"missing columns: {absent}")
        for c, kind in cols.items():
            if c in df.columns:
                check_column(rep, df, c, kind)
        rep.ok(f"{len(df):,} rows")

    print("\ncross-file checks")
    if "players.csv" in frames and "transactions.csv" in frames:
        players, tx = frames["players.csv"], frames["transactions.csv"]
        orphans = set(tx.player_id) - set(players.player_id)
        (rep.fail if orphans else rep.ok)(f"transactions reference {len(orphans)} unknown players")
        ts = pd.to_datetime(tx.timestamp, errors="coerce")
        days = (ts.max() - ts.min()).days if ts.notna().any() else 0
        (rep.fail if days < MIN_DAYS else rep.ok)(f"history covers {days} days (needs {MIN_DAYS}+ for the 30-day "
                                                 "window and 90-day baseline)")
        unknown = sorted(set(tx.ip_region[tx.ip_region != ""]) - set(JURISDICTION))
        (rep.warn if unknown else rep.ok)("IP regions " + (f"not in common.JURISDICTION (add them): {unknown[:5]}"
                                                           if unknown else "all mapped to a jurisdiction"))
        occ = sorted(set(players.occupation) - set(OCCUPATION_INCOME))
        (rep.warn if occ else rep.ok)("occupations " + (f"without a typical income in common.OCCUPATION_INCOME "
                                                        f"(occupation check skipped for them): {occ[:5]}" if occ
                                                        else "all have a typical income range"))
        dup = tx.txn_id.duplicated().sum()
        (rep.fail if dup else rep.ok)(f"{dup} duplicate txn_id values")
    print(f"\n{rep.fails} failure(s), {rep.warns} warning(s)")
    sys.exit(1 if rep.fails else 0)


if __name__ == "__main__":
    main()
