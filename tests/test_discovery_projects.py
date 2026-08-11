from __future__ import annotations

import subprocess
from pathlib import Path

from codex_monitor.projects import identify_project
from codex_monitor.sources.codex.discovery import discover_session_files


def test_discovers_historical_rollouts(codex_root: Path) -> None:
    files = discover_session_files([codex_root])
    assert len(files) == 1
    assert files[0].name.startswith("rollout-")


def test_non_git_directory_is_still_a_project(tmp_path: Path) -> None:
    project = tmp_path / "plain-project"
    project.mkdir()
    result = identify_project(str(project))
    assert result and result.name == "plain-project" and result.git_root is None


def test_git_sessions_group_at_repository_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    child = repo / "src" / "deep"
    child.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    result = identify_project(str(child))
    assert result and result.git_root == str(repo.resolve())
