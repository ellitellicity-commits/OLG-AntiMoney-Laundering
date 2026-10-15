"""Run the whole pipeline: generate data -> features -> detection -> validation.

Usage (from the repo root):
    python -m backend.pipeline.run_all            # full 5,000-player dataset
    python -m backend.pipeline.run_all --players 1500 --skip-generate
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_features  # noqa: E402
import detect  # noqa: E402
import generate_data  # noqa: E402
import validate  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--players", type=int, default=generate_data.CONFIG["n_players"])
    ap.add_argument("--seed", type=int, default=generate_data.CONFIG["seed"])
    ap.add_argument("--skip-generate", action="store_true", help="reuse existing data/synthetic files")
    args = ap.parse_args(argv)

    steps = []
    if not args.skip_generate:
        steps.append(("1/4 synthetic data", lambda: generate_data.main(["--players", str(args.players), "--seed", str(args.seed)])))
    steps += [("2/4 features", build_features.main), ("3/4 detection", detect.main), ("4/4 validation", validate.main)]
    for name, fn in steps:
        t0 = time.time()
        print(f"\n== {name} ==")
        fn()
        print(f"   ({time.time() - t0:.1f}s)")
    print("\nDone. Start the API with:  uvicorn backend.app.main:app --reload")


if __name__ == "__main__":
    main()
