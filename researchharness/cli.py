"""CLI entrypoint for the initial ResearchHarness foundation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TextIO
from uuid import uuid4

from .config import ResearchHarnessConfig, load_config, validate_environment
from .domain import ResearchSession, SessionState
from .domain.models import utc_now
from .persistence import SessionStore, WorkspaceLayout
from .session import ResumeManager
from .shell.commands import ShellCommandRegistry
from .shell.input_normalizer import combine_input_tokens, normalize_input
from .shell.repl import create_shell
from .shell.app import render_session_status, render_startup_summary


ROOT_COMMANDS = {"resume", "status", "pause"}


def build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rh", description="ResearchHarness bootstrap CLI")
    parser.add_argument(
        "input_parts",
        nargs="*",
        help="Natural-language input or a slash command such as /status.",
    )
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
    parser.add_argument("--focus", help="Persist an initial or updated focus summary.")
    parser.add_argument(
        "--plan-item",
        action="append",
        default=[],
        help="Persist a plan item. May be provided multiple times.",
    )
    parser.add_argument("--task-id", help="Persist the active task pointer.")
    return parser


def build_command_parser(command_name: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"rh {command_name}")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--session-id", help="Specific session id to operate on.")
    if command_name in {"resume", "pause"}:
        parser.add_argument("--focus", help="Updated focus summary.")
        parser.add_argument(
            "--plan-item",
            action="append",
            default=[],
            help="Persist a plan item. May be provided multiple times.",
        )
        parser.add_argument("--task-id", help="Persist the active task pointer.")
    return parser


def parse_args(argv: list[str] | None) -> tuple[str, argparse.Namespace]:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if raw_args and raw_args[0] in ROOT_COMMANDS:
        command_name = raw_args[0]
        return command_name, build_command_parser(command_name).parse_args(raw_args[1:])
    return "root", build_root_parser().parse_args(raw_args)


def _apply_session_updates(
    session: ResearchSession,
    *,
    focus: str | None = None,
    plan_items: list[str] | None = None,
    task_id: str | None = None,
) -> ResearchSession:
    if focus is not None:
        session.current_focus = focus
    if plan_items:
        session.plan_items = list(plan_items)
    if task_id is not None:
        session.active_task_id = task_id
    session.updated_at = utc_now()
    return session


def _handle_doctor(
    config, report, layout: WorkspaceLayout, session_id: str | None = None
) -> int:
    print(render_startup_summary(config, report, layout, session_id))
    if report.issues:
        print("issues:")
        for issue in report.issues:
            print(f"- {issue}")
    return 0


def _start_new_session(
    text: str,
    args: argparse.Namespace,
    store: SessionStore,
    config: ResearchHarnessConfig,
    report,
    layout: WorkspaceLayout,
) -> int:
    session_id = str(uuid4())
    session = ResearchSession(
        id=session_id,
        goal=text,
        workspace_root=str(config.workspace_root),
        transcript_path=str(layout.transcript_path(session_id)),
    )
    _apply_session_updates(
        session,
        focus=args.focus,
        plan_items=args.plan_item,
        task_id=args.task_id,
    )
    store.save(session)
    store.append_transcript_entry(
        session.id,
        event="session_started",
        message=f"Started session for goal: {session.goal}",
    )
    store.mark_command_start(session, "rh")
    store.mark_command_end(session, "rh", safe_boundary="Session bootstrap persisted")
    print(render_startup_summary(config, report, layout, session.id))
    print(render_session_status(session, store.load_transcript(session.id)))
    return 0


def _record_natural_language_turn(
    session: ResearchSession,
    text: str,
    store: SessionStore,
) -> int:
    store.mark_command_start(session, "user_turn")
    session.state = SessionState.ACTIVE
    store.save(session)
    store.append_transcript_entry(
        session.id,
        event="user_message",
        message=text,
    )
    store.mark_command_end(session, "user_turn", safe_boundary="User turn persisted")
    print("Recorded natural-language request in the active session.")
    print(render_session_status(session, store.load_transcript(session.id)))
    return 0


def _execute_shell_command(
    registry: ShellCommandRegistry,
    command_name: str,
    command_args: list[str],
    store: SessionStore,
) -> int:
    if not registry.has(command_name):
        print(f"Unknown shell command: /{command_name}", file=sys.stderr)
        return 1

    session = None if command_name == "help" else store.load_latest()
    if command_name != "help" and session is None:
        print("No active session available for shell commands.", file=sys.stderr)
        return 1

    output = registry.execute(command_name, session, store if session is not None else None, command_args)
    print(output)
    return 0


def _handle_root(
    args: argparse.Namespace,
    store: SessionStore,
    config: ResearchHarnessConfig,
    report,
    layout: WorkspaceLayout,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    if args.doctor:
        return _handle_doctor(config, report, layout)

    if not args.input_parts:
        return create_shell(
            store=store,
            config=config,
            report=report,
            layout=layout,
            input_stream=input_stream,
            output_stream=output_stream,
        ).run()

    registry = ShellCommandRegistry()
    normalized = normalize_input(combine_input_tokens(args.input_parts))
    if normalized.kind == "shell_command":
        return _execute_shell_command(
            registry,
            normalized.command_name or "",
            normalized.command_args,
            store,
        )
    if normalized.kind == "natural_language" and normalized.text:
        latest = store.load_latest()
        if latest is None:
            return _start_new_session(normalized.text, args, store, config, report, layout)
        return _record_natural_language_turn(latest, normalized.text, store)

    latest = store.load_latest()
    if latest is None:
        print(render_startup_summary(config, report, layout))
        return 0

    manager = ResumeManager(store)
    result = manager.resume()
    if result.session is None:
        print("No resumable session found.", file=sys.stderr)
        return 1
    session = result.session
    store.mark_command_start(session, "rh")
    store.append_transcript_entry(
        session.id,
        event="session_resumed",
        message="Resumed latest session via `rh`.",
    )
    store.mark_command_end(session, "rh", safe_boundary="Resume snapshot persisted")
    print(render_session_status(session, store.load_transcript(session.id), recovery_summary=result.recovery_summary))
    return 0


def _handle_resume(args: argparse.Namespace, store: SessionStore) -> int:
    manager = ResumeManager(store)
    result = manager.resume(session_id=args.session_id)
    if result.session is None:
        print("No resumable session found.", file=sys.stderr)
        return 1

    session = result.session
    store.mark_command_start(session, "resume")
    _apply_session_updates(
        session,
        focus=args.focus,
        plan_items=args.plan_item,
        task_id=args.task_id,
    )
    session.state = SessionState.ACTIVE
    store.save(session)
    store.append_transcript_entry(
        session.id,
        event="session_resumed",
        message="Session resumed.",
    )
    store.mark_command_end(session, "resume", safe_boundary="Resume snapshot persisted")
    print(render_session_status(session, store.load_transcript(session.id), recovery_summary=result.recovery_summary))
    return 0


def _handle_status(args: argparse.Namespace, store: SessionStore) -> int:
    session = store.load(args.session_id) if args.session_id else store.load_latest()
    if session is None:
        print("No saved sessions found.", file=sys.stderr)
        return 1
    status = store.latest_status() if not args.session_id else {
        "session": session,
        "transcript_entries": store.load_transcript(session.id),
        "recovery": dict(session.metadata.get("recovery", {})),
    }
    print(
        render_session_status(
            status["session"],
            status["transcript_entries"],
            recovery_summary=status["recovery"].get("summary"),
        )
    )
    return 0


def _handle_pause(args: argparse.Namespace, store: SessionStore) -> int:
    session = store.load(args.session_id) if args.session_id else store.load_latest()
    if session is None:
        print("No session available to pause.", file=sys.stderr)
        return 1
    store.mark_command_start(session, "pause")
    _apply_session_updates(
        session,
        focus=args.focus,
        plan_items=args.plan_item,
        task_id=args.task_id,
    )
    store.mark_safe_boundary(session, "Pause requested by user")
    store.append_transcript_entry(
        session.id,
        event="session_paused",
        message="Session paused at a safe boundary.",
    )
    session.state = SessionState.PAUSED
    store.save(session)
    store.mark_command_end(session, "pause", safe_boundary="Session paused safely")
    print(render_session_status(session, store.load_transcript(session.id)))
    return 0


def run(
    argv: list[str] | None = None,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    command_name, args = parse_args(argv)
    config = load_config(args.workspace)
    report = validate_environment(config)

    if not report.ok:
        for issue in report.issues:
            print(issue, file=sys.stderr)
        return 1

    layout = WorkspaceLayout.from_workspace_root(config.workspace_root).ensure()
    store = SessionStore(layout)

    if command_name == "root":
        return _handle_root(
            args,
            store,
            config,
            report,
            layout,
            input_stream=input_stream,
            output_stream=output_stream,
        )
    if command_name == "resume":
        return _handle_resume(args, store)
    if command_name == "status":
        return _handle_status(args, store)
    if command_name == "pause":
        return _handle_pause(args, store)
    print(f"Unsupported command: {command_name}", file=sys.stderr)
    return 1


def main(
    argv: list[str] | None = None,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    return run(argv, input_stream=input_stream, output_stream=output_stream)


if __name__ == "__main__":
    raise SystemExit(main())
