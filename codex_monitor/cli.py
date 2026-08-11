from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config, load_config
from .database import Database
from .indexer import Indexer
from .live import run as run_live
from .platform import current_platform
from .queries import projects, session_detail, sessions
from .setup import configure_codex_otel
from .web.server import serve


def _print_table(headers: list[str], rows: list[list[object]]) -> None:
    text = [["UNKNOWN / NOT EXPOSED" if value is None else str(value) for value in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in text:
        for index, value in enumerate(row):
            widths[index] = min(60, max(widths[index], len(value)))
    print("  ".join(header.ljust(widths[i]) for i, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in text:
        print("  ".join(value[: widths[i]].ljust(widths[i]) for i, value in enumerate(row)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-monitor", description="Local Codex observability")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--database", type=Path)
    sub = parser.add_subparsers(dest="command")
    setup = sub.add_parser("setup")
    setup.add_argument("--configure-otel", action="store_true",
                       help="append loopback OTel exporters to Codex config")
    setup.add_argument("--yes", action="store_true", help="confirm Codex config modification")
    sub.add_parser("live").add_argument("--once", action="store_true")
    session_cmd = sub.add_parser("sessions")
    session_cmd.add_argument("--search")
    session_cmd.add_argument("--limit", type=int, default=100)
    sub.add_parser("projects")
    show = sub.add_parser("show")
    show.add_argument("session")
    reindex = sub.add_parser("reindex")
    reindex.add_argument("--yes", action="store_true", help="confirm rebuilding the monitor cache")
    web = sub.add_parser("web")
    web.add_argument("--host")
    web.add_argument("--port", type=int)
    web.add_argument("--open", action="store_true")
    web.add_argument("--no-network", action="store_true", help="affirm local-only mode (the default)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    if args.database:
        config = Config(**{**config.__dict__, "database": args.database})
    db = Database(config.database_path)
    try:
        indexer = Indexer(config, db)
        if args.command == "setup":
            info = current_platform()
            checks = {
                "platform": "WSL2" if info.is_wsl else info.system,
                "codex_executable": str(info.executable("codex") or "not found"),
                "codex_home": str(info.codex_home),
                "codex_sessions": str(info.codex_home / "sessions"),
                "monitor_config": str(info.monitor_config),
                "database": str(config.database_path),
                "otel_logs_endpoint": f"http://{config.otel_host}:{config.otel_port}/v1/logs",
                "prompt_logging": "disabled" if not config.log_user_prompts else "enabled",
            }
            print("Codex Monitor Setup\n")
            for key, value in checks.items():
                print(f"✓ {key.replace('_', ' ').title()}: {value}")
            if args.configure_otel:
                if not args.yes:
                    print("\nPass --yes with --configure-otel after reviewing the endpoint.", file=sys.stderr)
                    return 2
                codex_config = info.codex_home / "config.toml"
                endpoint = f"http://{config.otel_host}:{config.otel_port}/v1/logs"
                result = configure_codex_otel(codex_config, endpoint)
                print(f"\n{result.reason}: {result.config_path}")
                if result.backup_path:
                    print(f"Backup: {result.backup_path}")
            else:
                print("\nDiscovery is read-only. Codex configuration has not been modified.")
            return 0
        if args.command == "reindex":
            if not args.yes:
                print("Reindex deletes only Codex Monitor's derived database. Pass --yes to continue.", file=sys.stderr)
                return 2
            print(json.dumps(indexer.reindex()))
            return 0
        indexer.scan()
        if args.command in {None, "live"}:
            run_live(config, db, bool(getattr(args, "once", False)))
        elif args.command == "sessions":
            data = sessions(db, min(max(args.limit, 1), 1000), args.search)
            _print_table(["PROJECT", "SESSION", "MODEL", "LAST ACTIVITY", "TOKENS"], [[x["project_name"], x["session_id"], x["model"], x["last_activity"], x["total_tokens"]] for x in data])
        elif args.command == "projects":
            data = projects(db)
            _print_table(["PROJECT", "PATH", "SESSIONS", "TOKENS", "LAST ACTIVITY"], [[x["name"], x["git_root"] or x["working_directory"], x["session_count"], x["total_tokens"], x["last_activity"]] for x in data])
        elif args.command == "show":
            detail = session_detail(db, args.session)
            if not detail:
                print(f"Session not found: {args.session}", file=sys.stderr)
                return 1
            print(json.dumps(detail, indent=2, default=str))
        elif args.command == "web":
            serve(config, db, args.host or config.web_host, args.port or config.web_port, args.open)
        return 0
    finally:
        db.close()
