from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from .database import Database

_SKIP = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build",
    "target", "coverage", "__pycache__", ".pytest_cache", ".ruff_cache", ".next",
}
_TECH = {
    "pyproject.toml": ("Python", "Packages Python code and records project tooling or dependencies."),
    "requirements.txt": ("Python", "Lists Python packages the project depends on."),
    "package.json": ("Node.js / JavaScript", "Defines JavaScript dependencies and runnable package scripts."),
    "tsconfig.json": ("TypeScript", "Configures static type checking for JavaScript-like source code."),
    "vite.config.ts": ("Vite", "Configures the frontend development and production build tool."),
    "dockerfile": ("Containers", "Defines a repeatable container image for running the software."),
    "docker-compose.yml": ("Containers", "Coordinates multiple containerized services."),
    "cargo.toml": ("Rust", "Defines a Rust package and its dependencies."),
    "go.mod": ("Go", "Defines a Go module and its dependencies."),
}
_EXTENSIONS = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "React / TypeScript",
    ".js": "JavaScript", ".jsx": "React / JavaScript", ".rs": "Rust",
    ".go": "Go", ".sql": "SQL", ".sh": "Shell scripting", ".ps1": "PowerShell",
}


def project_guide(db: Database, project_key: str) -> dict | None:
    row = db.connection.execute(
        "SELECT * FROM projects WHERE project_key=?", (project_key,)
    ).fetchone()
    if not row:
        return None
    root = Path(row["git_root"] or row["working_directory"]).expanduser().resolve(strict=False)
    if not root.is_dir():
        return {
            "project_key": project_key, "name": row["name"], "path": str(root),
            "available": False, "reason": "The associated project directory is not currently available.",
        }
    files, directories, truncated = _inventory(root)
    technologies = _technologies(files)
    areas = _areas(directories, files)
    main_files = [_explain_file(path) for path in _important(files)[:18]]
    concepts = _concepts(technologies, areas, files)
    return {
        "project_key": project_key,
        "name": row["name"],
        "path": str(root),
        "available": True,
        "rundown": _rundown(row["name"], technologies, areas),
        "technologies": technologies,
        "areas": areas,
        "main_files": main_files,
        "concepts": concepts,
        "connections": _connections(areas),
        "learning_path": _learning_path(technologies, concepts),
        "inventory": {"files_seen": len(files), "directories_seen": len(directories),
                      "truncated": truncated},
        "evidence_note": (
            "This deterministic guide inspects names and structure only, with a bounded read-only scan. "
            "It does not read source contents, execute project code, infer hidden intent, or prove behavior."
        ),
    }


def _inventory(root: Path, max_files: int = 600, max_depth: int = 4):
    files: list[Path] = []
    directories: set[str] = set()
    truncated = False
    for current, child_dirs, child_files in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root)
        depth = len(relative_dir.parts)
        child_dirs[:] = [
            name for name in child_dirs
            if name.lower() not in _SKIP and depth < max_depth
            and not (current_path / name).is_symlink()
        ]
        for directory in child_dirs:
            relative = (current_path / directory).relative_to(root)
            if relative.parts:
                directories.add(relative.parts[0])
        for filename in child_files:
            path = current_path / filename
            if path.is_symlink():
                continue
            files.append(path.relative_to(root))
            if len(files) >= max_files:
                truncated = True
                return sorted(files), sorted(directories), truncated
    return sorted(files), sorted(directories), truncated


def _technologies(files: list[Path]) -> list[dict[str, str | int]]:
    names = {path.name.lower() for path in files}
    detected: dict[str, dict[str, str | int]] = {}
    for marker, (name, explanation) in _TECH.items():
        if marker in names:
            detected[name] = {"name": name, "evidence": marker, "explanation": explanation}
    extensions = Counter(_EXTENSIONS.get(path.suffix.lower()) for path in files)
    for name, count in extensions.most_common():
        if name and name not in detected:
            detected[name] = {
                "name": name, "evidence": f"{count} matching source file(s)",
                "explanation": f"The repository contains source files commonly used for {name}.",
            }
    return list(detected.values())


def _areas(directories: list[str], files: list[Path]) -> list[dict[str, str]]:
    roots = {item.lower() for item in directories}
    names = {path.name.lower() for path in files}
    candidates = [
        ({"frontend", "web", "ui", "client"}, "User interface", "Code presented to and interacted with by a user."),
        ({"backend", "server", "api"}, "Backend / API", "Server-side logic, data access, and HTTP endpoints."),
        ({"tests", "test", "spec"}, "Automated tests", "Repeatable checks that protect expected behavior."),
        ({"docs", "documentation"}, "Documentation", "Written explanations for users and contributors."),
        ({"scripts", "bin"}, "Automation scripts", "Repeatable development, build, or operational tasks."),
        ({"migrations", "database", "db"}, "Data storage", "Database schema or data-access responsibilities."),
    ]
    result = [
        {"name": name, "explanation": explanation}
        for markers, name, explanation in candidates if roots & markers
    ]
    if {"package.json", "vite.config.ts"} & names:
        result.append({"name": "Build configuration", "explanation": "Tools transform source code into runnable or distributable software."})
    return result


def _important(files: list[Path]) -> list[Path]:
    preferred = {
        "readme.md", "agents.md", "pyproject.toml", "package.json", "tsconfig.json",
        "vite.config.ts", "dockerfile", "docker-compose.yml", "main.py", "app.py",
        "server.py", "cli.py", "index.ts", "index.tsx", "main.ts", "main.tsx",
        "config.py", "database.py", "schema.sql",
    }
    return sorted(files, key=lambda path: (path.name.lower() not in preferred, len(path.parts), str(path)))


def _explain_file(path: Path) -> dict[str, str]:
    name = path.name.lower()
    exact = {
        "readme.md": "The human-facing introduction, setup instructions, and project overview.",
        "agents.md": "Instructions that guide future coding-agent work in this repository.",
        "pyproject.toml": "Python package metadata, dependencies, build settings, and tool configuration.",
        "package.json": "JavaScript package metadata, dependencies, and runnable scripts.",
        "database.py": "Usually owns database connection, schema, or persistence behavior.",
        "server.py": "Usually starts a server and connects HTTP routes to application logic.",
        "cli.py": "Usually defines terminal commands and dispatches them to application functions.",
        "main.tsx": "Usually starts a React interface and connects major UI components.",
        "main.py": "A likely Python entry point where application startup begins.",
    }
    explanation = exact.get(name)
    if not explanation:
        explanation = {
            ".py": "A Python module containing application logic or tests.",
            ".tsx": "A typed React component combining interface structure and behavior.",
            ".ts": "A TypeScript module with statically checked JavaScript logic.",
            ".sql": "SQL defining or querying relational data.",
            ".sh": "A shell script automating command-line work.",
            ".md": "Markdown documentation intended for human readers.",
        }.get(path.suffix.lower(), "A project file whose exact responsibility requires reading its contents.")
    return {"path": str(path), "explanation": explanation}


def _concepts(technologies, areas, files: list[Path]) -> list[dict[str, str]]:
    tech = {item["name"] for item in technologies}
    area = {item["name"] for item in areas}
    concepts = []
    candidates = [
        ("Python" in tech, "Modules and packages", "Python files form modules; packages group modules behind stable imports."),
        (bool({"TypeScript", "React / TypeScript"} & tech), "Static typing", "TypeScript catches many mismatched values and interfaces before code runs."),
        ("React / TypeScript" in tech, "Component-based UI", "React builds interfaces from reusable components driven by data and state."),
        ("Backend / API" in area, "API boundaries", "An API gives the frontend or another client a stable way to request backend behavior or data."),
        ("Data storage" in area or any(path.suffix == ".sql" for path in files), "Relational data", "Tables, keys, and queries organize connected records without duplicating everything."),
        ("Automated tests" in area, "Regression testing", "Automated tests make expected behavior repeatable and warn when later changes break it."),
        ("Build configuration" in area, "Build pipeline", "Build tools validate and transform source files into artifacts that users can run."),
        (True, "Separation of concerns", "Dividing interface, storage, business logic, and infrastructure makes changes easier to reason about."),
    ]
    for condition, name, explanation in candidates:
        if condition:
            concepts.append({"name": name, "explanation": explanation})
    return concepts[:8]


def _connections(areas) -> list[str]:
    names = {item["name"] for item in areas}
    result = []
    if "User interface" in names and "Backend / API" in names:
        result.append("The user interface likely requests data or operations through the backend/API boundary.")
    if "Backend / API" in names and "Data storage" in names:
        result.append("The backend likely translates application requests into database reads and writes.")
    if "Automated tests" in names:
        result.append("Automated tests exercise other layers to verify their observable behavior remains stable.")
    if "Build configuration" in names and "User interface" in names:
        result.append("The build tooling converts frontend source into browser-ready assets.")
    return result or ["The exact runtime connections require source-level inspection; this guide does not guess them from filenames alone."]


def _rundown(name: str, technologies, areas) -> str:
    tech = ", ".join(item["name"] for item in technologies[:4]) or "an unidentified technology stack"
    layers = ", ".join(item["name"].lower() for item in areas[:4]) or "a compact repository structure"
    return f"{name} appears to use {tech}. Its visible structure includes {layers}."


def _learning_path(technologies, concepts) -> list[str]:
    items = [f"Learn the basics of {item['name']} and find where it enters the application." for item in technologies[:3]]
    items.extend(f"Trace one example of {item['name'].lower()} through the repository." for item in concepts[:3])
    items.append("Choose one user-visible behavior and follow it from entry point to test or stored data.")
    return items[:7]
