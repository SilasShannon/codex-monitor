from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from codex_monitor.config import Config
from codex_monitor.database import Database


@pytest.fixture
def codex_root(tmp_path: Path) -> Path:
    root = tmp_path / ".codex"
    target = root / "sessions" / "2026" / "08" / "10"
    target.mkdir(parents=True)
    source = Path(__file__).parent / "fixtures" / "rollout-basic.jsonl"
    shutil.copy2(source, target / "rollout-2026-test.jsonl")
    return root


@pytest.fixture
def config(tmp_path: Path, codex_root: Path) -> Config:
    return Config(data_roots=(codex_root,), cache_directory=tmp_path / "cache", git_enabled=False)


@pytest.fixture
def db(config: Config):
    database = Database(config.database_path)
    yield database
    database.close()
