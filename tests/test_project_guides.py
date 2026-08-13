from __future__ import annotations

from codex_monitor.project_guides import _inventory, project_guide


def test_project_guide_explains_structure_without_source_contents(db, tmp_path) -> None:
    root = tmp_path / "learning-app"
    (root / "frontend" / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "README.md").write_text("SECRET SOURCE CONTENT")
    (root / "package.json").write_text("{}")
    (root / "frontend" / "src" / "main.tsx").write_text("private implementation")
    (root / "tests" / "test_app.py").write_text("private test")
    db.connection.execute(
        "INSERT INTO projects VALUES(?,?,?,?)", ("guide-key", "learning-app", str(root), str(root))
    )
    guide = project_guide(db, "guide-key")
    assert guide and guide["available"]
    assert any(item["name"] == "Node.js / JavaScript" for item in guide["technologies"])
    assert any(item["name"] == "User interface" for item in guide["areas"])
    assert any(item["path"] == "README.md" for item in guide["main_files"])
    assert "SECRET SOURCE CONTENT" not in str(guide)
    assert "does not read source contents" in guide["evidence_note"]


def test_project_guide_requires_known_project(db) -> None:
    assert project_guide(db, "missing") is None


def test_project_guide_handles_unavailable_directory(db, tmp_path) -> None:
    missing = tmp_path / "gone"
    db.connection.execute(
        "INSERT INTO projects VALUES(?,?,?,?)", ("gone-key", "gone", str(missing), None)
    )
    guide = project_guide(db, "gone-key")
    assert guide and not guide["available"]


def test_project_guide_prunes_dependencies_and_symlinks(db, tmp_path) -> None:
    root = tmp_path / "safe-app"
    (root / "node_modules" / "private-package").mkdir(parents=True)
    (root / "node_modules" / "private-package" / "package.json").write_text("hidden")
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("pass")
    (root / "outside").symlink_to(tmp_path, target_is_directory=True)
    db.connection.execute(
        "INSERT INTO projects VALUES(?,?,?,?)", ("safe-key", "safe-app", str(root), str(root))
    )
    guide = project_guide(db, "safe-key")
    assert guide and guide["available"]
    serialized = str(guide)
    assert "private-package" not in serialized
    assert not any(item["path"].startswith("outside") for item in guide["main_files"])


def test_bounded_inventory_is_deterministic(tmp_path, monkeypatch) -> None:
    root = tmp_path / "ordered-app"
    root.mkdir()
    walk_result = [(str(root), ["zeta", "Alpha"], ["z.py", "A.py", "middle.py"])]
    monkeypatch.setattr("codex_monitor.project_guides.os.walk", lambda *args, **kwargs: walk_result)

    files, directories, truncated = _inventory(root, max_files=2)

    assert files == [root.joinpath("A.py").relative_to(root), root.joinpath("middle.py").relative_to(root)]
    assert directories == ["Alpha", "zeta"]
    assert truncated
