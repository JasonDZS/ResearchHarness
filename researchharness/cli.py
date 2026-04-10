"""CLI entrypoint for the initial ResearchHarness foundation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from uuid import uuid4

from .config import load_config, validate_environment
from .domain import ResearchSession
from .persistence import SessionStore, WorkspaceLayout
from .shell.app import render_startup_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rh", description="ResearchHarness bootstrap CLI")
    parser.add_argument("goal", nargs="?", help="Optional research goal to bootstrap a session.")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root where `.research/` should be created.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Validate the local environment and print a diagnostic report.",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.workspace)
    report = validate_environment(config)

    if not report.ok:
        for issue in report.issues:
            print(issue, file=sys.stderr)
        return 1

    layout = WorkspaceLayout.from_workspace_root(config.workspace_root).ensure()
    session_id: str | None = None

    if args.goal:
        session_id = str(uuid4())
        store = SessionStore(layout)
        store.save(
            ResearchSession(
                id=session_id,
                goal=args.goal,
                workspace_root=str(config.workspace_root),
                transcript_path=str(layout.transcript_path(session_id)),
            )
        )

    if args.doctor:
        print(render_startup_summary(config, report, layout, session_id))
        if report.issues:
            print("issues:")
            for issue in report.issues:
                print(f"- {issue}")
        return 0

    print(render_startup_summary(config, report, layout, session_id))
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())

