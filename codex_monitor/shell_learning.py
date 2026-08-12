from __future__ import annotations

import json
import re
import shlex

from .database import Database

_SECRET = re.compile(
    r"(?i)\b([A-Z_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|AUTH)[A-Z_]*)=([^\s]+)"
)

_COMMANDS = {
    "pytest": ("Testing", "Runs Python tests so behavior can be checked repeatedly.", "Read-only to project files"),
    "npm": ("JavaScript tooling", "Runs package scripts or manages JavaScript dependencies.", "Depends on subcommand"),
    "git": ("Version control", "Inspects or operates on Git history and working-tree state.", "Depends on subcommand"),
    "rg": ("Search", "Searches text quickly across files while respecting useful ignore rules.", "Read-only"),
    "grep": ("Search", "Finds lines matching a text pattern.", "Read-only"),
    "find": ("File discovery", "Locates files and directories that match given conditions.", "Usually read-only"),
    "sed": ("Text processing", "Selects or transforms text streams; without in-place mode it only prints output.", "Depends on flags"),
    "curl": ("Networking", "Makes an HTTP request, often to verify an API or download data.", "Network access; may write output"),
    "gh": ("GitHub CLI", "Uses GitHub's command-line client to inspect or change repository hosting data.", "Depends on subcommand; may change remote state"),
    "rm": ("File management", "Removes files or directories named by its arguments.", "Destructive: deleted data may not be recoverable"),
    "node": ("JavaScript execution", "Runs JavaScript outside a browser.", "Depends on the program"),
    "powershell": ("PowerShell", "Runs a PowerShell command or script.", "Depends on the script"),
    "powershell.exe": ("PowerShell", "Runs a Windows PowerShell command from the current environment.", "Depends on the script"),
    "python": ("Python execution", "Runs Python code or a Python module.", "Depends on the program"),
    "python3": ("Python execution", "Runs Python code or a Python module.", "Depends on the program"),
    "ruff": ("Static analysis", "Checks Python code for style problems and likely mistakes.", "Read-only unless --fix is used"),
}


def shell_lessons(db: Database, limit: int = 50) -> dict:
    rows = db.connection.execute(
        """SELECT c.call_id,c.session_id,c.timestamp,c.arguments_json,r.success,
                  p.name project_name
           FROM tool_calls c LEFT JOIN tool_results r USING(call_id,session_id)
           LEFT JOIN sessions s USING(session_id) LEFT JOIN projects p USING(project_key)
           WHERE c.name IN ('exec_command','shell')
           ORDER BY c.timestamp DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    lessons = []
    for row in rows:
        command = _command(row["arguments_json"])
        if not command:
            continue
        lessons.append(explain_command(command, dict(row)))
    return {
        "summary": {
            "commands": len(lessons),
            "projects": len({item["project"] for item in lessons}),
            "categories": len({item["category"] for item in lessons}),
            "failed": sum(item["success"] is False for item in lessons),
        },
        "lessons": lessons,
        "evidence_note": (
            "Explanations are deterministic learning aids based on command syntax. "
            "They do not prove Codex's private intent, and sensitive-looking assignments are redacted."
        ),
    }


def explain_command(command: str, evidence: dict | None = None) -> dict:
    safe = _SECRET.sub(lambda match: f"{match.group(1)}=<redacted>", command.strip())
    try:
        tokens = shlex.split(safe, posix=True)
    except ValueError:
        tokens = safe.split()
    wrapper = tokens[0].rsplit("/", 1)[-1] if tokens else None
    if wrapper in {"bash", "sh", "zsh"} and len(tokens) >= 3 and "c" in tokens[1]:
        try:
            tokens = shlex.split(tokens[2], posix=True)
        except ValueError:
            tokens = tokens[2].split()
    executable_index = next(
        (index for index, token in enumerate(tokens) if token.rsplit("/", 1)[-1] in _COMMANDS),
        next((index for index, token in enumerate(tokens) if "=" not in token or token.startswith("-")), 0),
    )
    executable = tokens[executable_index].rsplit("/", 1)[-1] if tokens else "unknown"
    category, purpose, safety = _COMMANDS.get(
        executable, ("Shell", "Runs a shell command observed in the Codex session.", "Review before running manually")
    )
    if executable == "git" and len(tokens) > executable_index + 1:
        purpose, safety = _git(tokens[executable_index + 1])
    elif executable == "npm" and len(tokens) > executable_index + 1:
        purpose = f"Uses npm's {tokens[executable_index + 1]} operation for this JavaScript project."
    parts = _parts(tokens, executable_index)
    if wrapper in {"bash", "sh", "zsh"}:
        parts.insert(0, {"syntax": f"{wrapper} -c", "meaning": "A shell wrapper used to run the inner command text."})
    evidence = evidence or {}
    return {
        "command": safe[:500],
        "executable": executable,
        "category": category,
        "purpose": purpose,
        "safety": safety,
        "parts": parts,
        "learning_value": _learning_value(category),
        "project": evidence.get("project_name") or "Unassigned",
        "session_id": evidence.get("session_id"),
        "timestamp": evidence.get("timestamp"),
        "success": None if evidence.get("success") is None else bool(evidence["success"]),
    }


def _command(arguments_json: str | None) -> str | None:
    try:
        value = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return None
    command = value.get("cmd", value.get("command")) if isinstance(value, dict) else None
    if isinstance(command, list):
        return " ".join(shlex.quote(str(part)) for part in command)
    return command if isinstance(command, str) else None


def _parts(tokens: list[str], executable_index: int = 0) -> list[dict[str, str]]:
    if not tokens:
        return []
    result = []
    for assignment in tokens[:executable_index]:
        meaning = (
            "An environment value applied only to this command."
            if "=" in assignment else "Setup syntax that runs before the highlighted program."
        )
        result.append({"syntax": assignment, "meaning": meaning})
    result.append({"syntax": tokens[executable_index], "meaning": "The program being executed."})
    for token in tokens[executable_index + 1:executable_index + 7]:
        if token in {"|", "&&", "||"}:
            meaning = "Connects commands or controls when the next command runs."
        elif token.startswith("-"):
            meaning = "An option that changes the program's behavior; check its help before reusing it."
        else:
            meaning = "An argument, such as a subcommand, path, pattern, or value."
        result.append({"syntax": token, "meaning": meaning})
    return result


def _git(subcommand: str) -> tuple[str, str]:
    read_only = {"status", "log", "diff", "show", "branch", "rev-parse"}
    if subcommand in read_only:
        return f"Uses git {subcommand} to inspect repository state or history.", "Read-only"
    return f"Uses git {subcommand}, which may change repository or remote state.", "Potentially modifies Git state"


def _learning_value(category: str) -> str:
    return {
        "Testing": "Learn how automated checks turn expected behavior into repeatable feedback.",
        "Search": "Learn how developers locate definitions and evidence before changing code.",
        "Version control": "Learn how Git records, compares, and coordinates code changes.",
        "Text processing": "Learn how shell tools transform streams and compose into small workflows.",
        "Networking": "Learn how command-line clients interact with HTTP services and APIs.",
    }.get(category, "Reviewing real commands builds familiarity with repeatable developer workflows.")
