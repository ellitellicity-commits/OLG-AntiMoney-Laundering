"""Step 3b - Cross-seed validation: does the system work on players it has never seen?

The AI risk model is trained on the seed-42 population (train_model.py). This step builds
completely new populations with other seeds (same kinds of planted risk, different people,
different numbers), scores them with that already-trained model and the unchanged rules,
and measures the whole system. Each test population lives in a temporary folder that is
deleted afterwards; the demo data in data/ is never touched.

Output: data/scores/cross_seed.json (read by validate.py into docs/VALIDATION.md)

Usage:  python backend/pipeline/cross_seed.py [--seeds 7 2027]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import roc_auc_score

from common import MODELS, SCORES, load_metadata

HERE = Path(__file__).resolve().parent
DEFAULT_SEEDS = [7, 2027]


def step(script: str, data_dir: Path, *args: str):
    env = os.environ | {"OLG_DATA_DIR": str(data_dir)}
    subprocess.run([sys.executable, str(HERE / script), *args], env=env, check=True,
                   stdout=subprocess.DEVNULL, cwd=HERE.parents[1])


def score_with_saved_model(model_path: str):
    """Child mode (OLG_DATA_DIR set): score this population with the seed-42 model; no retraining."""
    from common import FEATURES
    from train_model import score_population
    f = pd.read_parquet(FEATURES / "player_features.parquet").set_index("player_id")
    score_population(joblib.load(model_path), f).reset_index().to_parquet(FEATURES / "ml_scores.parquet", index=False)


def evaluate(data_dir: Path, seed: int) -> dict:
    scores = pd.read_csv(data_dir / "scores" / "risk_scores.csv")
    alerts = json.loads((data_dir / "scores" / "alerts.json").read_text(encoding="utf-8"))
    labels = pd.read_csv(data_dir / "synthetic" / "scenario_labels.csv")
    injected = set(labels.player_id)
    s = scores.set_index("player_id")
    alerted = set(s.index[s.alert])
    normal = s.index.difference(list(injected))
    order = scores.player_id  # already ranked by score, points, AI probability
    conf = pd.DataFrame([{"level": a["confidence"]["level"], "hit": a["player_id"] in injected} for a in alerts])
    fps = conf[~conf.hit]
    return {
        "seed": seed, "players": len(s), "injected": len(injected), "alerts": len(alerted),
        "recall_all": round(len(alerted & injected) / len(injected), 3),
        "recall_by_scenario": {k: round(len(alerted & set(g.player_id)) / len(g), 3)
                               for k, g in labels.groupby("scenario")},
        "false_positive_rate": round(len(alerted - injected) / len(normal), 4),
        "precision_at_50": round(sum(p in injected for p in order.head(50)) / 50, 3),
        "precision_at_100": round(sum(p in injected for p in order.head(100)) / 100, 3),
        "ml_roc_auc": round(float(roc_auc_score(s.index.isin(list(injected)), s.ml_probability.fillna(0))), 4),
        "precision_high_medium_confidence": round(float(conf[conf.level != "Low"].hit.mean()), 3),
        "false_positives_in_low_confidence": f"{(fps.level == 'Low').sum()} of {len(fps)}",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    ap.add_argument("--score-model", help=argparse.SUPPRESS)  # internal: child scoring mode
    args = ap.parse_args()
    if args.score_model:
        score_with_saved_model(args.score_model)
        return

    model_path = MODELS / "risk_model.joblib"
    if not model_path.exists():
        sys.exit("Run train_model.py first (the seed-42 model is what gets tested).")
    trained_on = load_metadata()["seed"]
    results = []
    for seed in args.seeds:
        if seed == trained_on:
            continue
        tmp = Path(tempfile.mkdtemp(prefix=f"olg_seed{seed}_"))
        try:
            step("generate_data.py", tmp, "--seed", str(seed))
            step("build_features.py", tmp)
            step("cross_seed.py", tmp, "--score-model", str(model_path))
            step("detect.py", tmp)
            results.append(evaluate(tmp, seed))
            r = results[-1]
            print(f"seed {seed}: recall {r['recall_all']:.0%}, false positives {r['false_positive_rate']:.2%}, "
                  f"p@100 {r['precision_at_100']:.0%}, AI ROC-AUC {r['ml_roc_auc']}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    SCORES.mkdir(parents=True, exist_ok=True)
    (SCORES / "cross_seed.json").write_text(json.dumps({"trained_on_seed": trained_on, "results": results}, indent=2)
                                           + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
