"""Builds a small end-to-end dataset once per test session in a temp directory.

The pipeline scripts read OLG_DATA_DIR at import time (backend/pipeline/common.py), so each step runs
in its own process pointed at the temp folder. data/ and docs/ are never touched.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "backend" / "pipeline"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PIPELINE))

N_PLAYERS = 1200
SEED = 11


def run_step(data_dir: Path, script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(PIPELINE / script), *args], env=os.environ | {"OLG_DATA_DIR": str(data_dir)},
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL)


def generate(data_dir: Path) -> None:
    run_step(data_dir, "generate_data.py", "--players", str(N_PLAYERS), "--seed", str(SEED))


def evaluate(data_dir: Path) -> dict:
    """validate.evaluate() on the temp data; validate.main() is not run because it rewrites docs/VALIDATION.md."""
    code = "import json, validate; print(json.dumps(validate.evaluate()))"
    out = subprocess.run([sys.executable, "-c", code], env=os.environ | {"OLG_DATA_DIR": str(data_dir)},
                         check=True, cwd=PIPELINE, capture_output=True, text=True, encoding="utf-8").stdout
    return json.loads(out)


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("data")
    generate(d)
    for script in ["build_features.py", "train_model.py", "detect.py"]:
        run_step(d, script)
    return d
