"""Built-in slash commands for the lightweight ResearchHarness shell."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from ..domain import Checkpoint, ResearchSession
from ..persistence import SessionStore, TaskStore
from ..session import TaskPlanner
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
            "task": ShellCommand(
                "task",
                "/task <add|focus> ...",
                "Add a task or focus a persisted task.",
            ),
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
        if name == "task":
            return self._handle_task_command(session, store, args)
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

    @staticmethod
    def _handle_task_command(
        session: ResearchSession,
        store: SessionStore,
        args: list[str],
    ) -> str:
        if not args:
            return "Usage: /task <add|focus> ..."

        planner = TaskPlanner(TaskStore(store))
        action = args[0]
        if action == "add":
            if len(args) < 2:
                return "Usage: /task add <text>"
            task = planner.add_task(session.id, " ".join(args[1:]))
            refreshed = store.load(session.id)
            return f"Added task {task.id}: {task.title}\n{render_tasks_view(refreshed)}"

        if action == "focus":
            if len(args) != 2:
                return "Usage: /task focus <id>"
            task = planner.focus_task(session.id, args[1])
            refreshed = store.load(session.id)
            return f"Focused task {task.id}: {task.title}\n{render_session_status(refreshed, store.load_transcript(session.id))}"

        return f"Unknown task command: {action}"
