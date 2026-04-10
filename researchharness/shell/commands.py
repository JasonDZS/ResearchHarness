"""Built-in slash commands for the lightweight ResearchHarness shell."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from ..domain import Checkpoint, ResearchSession
from ..persistence import SessionStore
from .app import (
    render_checkpoints_view,
    render_command_help,
    render_plan_view,
    render_session_status,
    render_tasks_view,
)


@dataclass(frozen=True)
class ShellCommand:
    """Registered shell command metadata."""

    name: str
    usage: str
    description: str


class ShellCommandRegistry:
    """Registry for built-in slash commands."""

    def __init__(self) -> None:
        self._commands = {
            "help": ShellCommand("help", "/help", "Show available shell commands."),
            "status": ShellCommand(
                "status", "/status", "Show session status, active task, and approvals."
            ),
            "plan": ShellCommand("plan", "/plan", "Show the persisted plan snapshot."),
            "tasks": ShellCommand("tasks", "/tasks", "Show persisted tasks."),
            "checkpoint": ShellCommand(
                "checkpoint",
                "/checkpoint [summary]",
                "Show checkpoints or create a manual checkpoint when a summary is provided.",
            ),
        }

    def list_commands(self) -> list[ShellCommand]:
        return [self._commands[name] for name in sorted(self._commands)]

    def has(self, name: str) -> bool:
        return name in self._commands

    def execute(
        self,
        name: str,
        session: ResearchSession | None,
        store: SessionStore | None,
        args: list[str] | None = None,
    ) -> str:
        if name == "help":
            return render_command_help(self.list_commands())

        if session is None or store is None:
            raise ValueError("An active session is required for this command.")

        args = list(args or [])
        if name == "status":
            return render_session_status(session, store.load_transcript(session.id))
        if name == "plan":
            return render_plan_view(session)
        if name == "tasks":
            return render_tasks_view(session)
        if name == "checkpoint":
            if args:
                checkpoint = Checkpoint(
                    id=str(uuid4()),
                    summary=" ".join(args),
                )
                session.checkpoints.append(checkpoint)
                store.save(session)
                store.append_transcript_entry(
                    session.id,
                    event="checkpoint_created",
                    message=checkpoint.summary,
                    metadata={"checkpoint_id": checkpoint.id},
                )
            return render_checkpoints_view(session)
        raise ValueError(f"Unknown shell command: {name}")

