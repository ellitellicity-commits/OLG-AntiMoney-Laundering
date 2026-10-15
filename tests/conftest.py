"""Builds a small end-to-end dataset once per test session in a temp directory."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend" / "pipeline"))

import build_features  # noqa: E402
import detect  # noqa: E402
import generate_data  # noqa: E402
import validate  # noqa: E402

N_PLAYERS = 1200
SEED = 11


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("data")
    generate_data.main(["--players", str(N_PLAYERS), "--seed", str(SEED), "--out", str(d / "synthetic")])
    build_features.build(d / "synthetic", d / "features")
    detect.run(d / "features", d / "scores")
    validate.run(d / "scores", d / "synthetic", d / "docs", d / "features")
    return d


@pytest.fixture(scope="session")
def client(data_dir):
    from fastapi.testclient import TestClient

    from backend.app import main
    from backend.app.store import DataStore

    main.store = DataStore(data_dir)
    with TestClient(main.app) as c:
        yield c
