"""Persistent terminal shell / REPL for ResearchHarness."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import TextIO
from uuid import uuid4

from ..config import EnvironmentReport, ResearchHarnessConfig
from ..domain import ResearchSession, SessionState
from ..domain.models import utc_now
from ..persistence import SessionStore
from ..persistence.workspace import WorkspaceLayout
from ..session import ResumeManager
from .app import render_session_status, render_startup_summary
from .commands import ShellCommandRegistry
from .input_normalizer import normalize_input


@dataclass
class ResearchShell:
    """Persistent interactive shell that reuses the session-first runtime state."""

    store: SessionStore
    config: ResearchHarnessConfig
    report: EnvironmentReport
    layout: WorkspaceLayout
    input_stream: TextIO
    output_stream: TextIO

    def __post_init__(self) -> None:
        self.registry = ShellCommandRegistry()
        self.session: ResearchSession | None = None
        self.recovery_summary: str | None = None

    def run(self) -> int:
        self._bootstrap()

        while True:
            self._write("rh> ", newline=False)
            raw_line = self.input_stream.readline()
            if raw_line == "":
                return self._exit_shell("EOF received; exiting shell safely.")

            normalized = normalize_input(raw_line)
            if normalized.kind == "empty":
                continue

            if normalized.kind == "shell_command":
                command_name = normalized.command_name or ""
                if command_name in {"exit", "quit"}:
                    return self._exit_shell("Shell exited.")
                if command_name == "pause":
                    return self._pause_shell()
                exit_code = self._execute_shell_command(
                    command_name=command_name,
                    command_args=normalized.command_args,
                )
                if exit_code != 0:
                    return exit_code
                continue

            if normalized.kind == "natural_language" and normalized.text:
                self._handle_natural_language(normalized.text)

        return 0

    def _bootstrap(self) -> None:
        latest = self.store.load_latest()
        if latest is None:
            self._write(render_startup_summary(self.config, self.report, self.layout))
            self._write("No active session. Enter a research goal to begin. Use /help for commands.")
            return

        result = ResumeManager(self.store).resume()
        self.session = result.session
        self.recovery_summary = result.recovery_summary
        if self.session is not None:
            self._write(render_session_status(
                self.session,
                self.store.load_transcript(self.session.id),
                recovery_summary=self.recovery_summary,
            ))

    def _handle_natural_language(self, text: str) -> None:
        if self.session is None:
            session_id = str(uuid4())
            self.session = ResearchSession(
                id=session_id,
                goal=text,
                workspace_root=str(self.config.workspace_root),
                transcript_path=str(self.layout.transcript_path(session_id)),
            )
            self.session.updated_at = utc_now()
            self.store.save(self.session)
            self.store.append_transcript_entry(
                self.session.id,
                event="session_started",
                message=f"Started session for goal: {self.session.goal}",
            )
            self._write(render_startup_summary(self.config, self.report, self.layout, self.session.id))
            self._write(render_session_status(self.session, self.store.load_transcript(self.session.id)))
            return

        self.store.mark_command_start(self.session, "user_turn")
        self.session.state = SessionState.ACTIVE
        self.store.save(self.session)
        self.store.append_transcript_entry(
            self.session.id,
            event="user_message",
            message=text,
        )
        self.store.mark_command_end(self.session, "user_turn", safe_boundary="User turn persisted")
        self._write("Recorded natural-language request in the active session.")
        self._write(render_session_status(self.session, self.store.load_transcript(self.session.id)))

    def _execute_shell_command(self, command_name: str, command_args: list[str]) -> int:
        if not self.registry.has(command_name):
            self._write(f"Unknown shell command: /{command_name}")
            return 1

        if command_name != "help" and self.session is None:
            self._write("No active session available for shell commands.")
            return 1

        if self.session is not None:
            self.session = self.store.load(self.session.id)

        output = self.registry.execute(
            command_name,
            self.session,
            self.store if self.session is not None else None,
            command_args,
        )
        if self.session is not None:
            self.session = self.store.load(self.session.id)
        self._write(output)
        return 0

    def _pause_shell(self) -> int:
        if self.session is None:
            self._write("No session available to pause.")
            return 1
        self.store.mark_command_start(self.session, "pause")
        self.store.mark_safe_boundary(self.session, "Pause requested by user from interactive shell")
        self.store.append_transcript_entry(
            self.session.id,
            event="session_paused",
            message="Session paused from interactive shell.",
        )
        self.session.state = SessionState.PAUSED
        self.store.save(self.session)
        self.store.mark_command_end(self.session, "pause", safe_boundary="Session paused safely")
        self._write(render_session_status(self.session, self.store.load_transcript(self.session.id)))
        self._write("Shell paused.")
        return 0

    def _exit_shell(self, message: str) -> int:
        if self.session is not None:
            self.store.mark_command_start(self.session, "exit")
            self.store.mark_safe_boundary(self.session, "Exit requested by user from interactive shell")
            self.store.append_transcript_entry(
                self.session.id,
                event="session_waiting_for_user",
                message=message,
            )
            self.session.state = SessionState.WAITING_FOR_USER
            self.store.save(self.session)
            self.store.mark_command_end(self.session, "exit", safe_boundary="Shell exit persisted")
        self._write(message)
        return 0

    def _write(self, text: str, *, newline: bool = True) -> None:
        self.output_stream.write(text)
        if newline:
            self.output_stream.write("\n")
        self.output_stream.flush()


def create_shell(
    store: SessionStore,
    config: ResearchHarnessConfig,
    report: EnvironmentReport,
    layout: WorkspaceLayout,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> ResearchShell:
    return ResearchShell(
        store=store,
        config=config,
        report=report,
        layout=layout,
        input_stream=input_stream or sys.stdin,
        output_stream=output_stream or sys.stdout,
    )
