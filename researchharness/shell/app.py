"""Rendering helpers for the lightweight v0.1 CLI bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..domain import Checkpoint, ResearchSession, Task
from ..config import EnvironmentReport, ResearchHarnessConfig
from ..persistence import TranscriptEntry
from ..persistence.workspace import WorkspaceLayout

if TYPE_CHECKING:
    from .commands import ShellCommand


def _resolve_active_task(session: ResearchSession) -> Task | None:
    if not session.active_task_id:
        return None
    for task in session.tasks:
        if task.id == session.active_task_id:
            return task
    return None


def _count_pending_approvals(session: ResearchSession) -> int:
    pending = sum(1 for checkpoint in session.checkpoints if checkpoint.requires_approval)
    pending += len(session.metadata.get("pending_approvals", []))
    return pending


def render_startup_summary(
    config: ResearchHarnessConfig,
    report: EnvironmentReport,
    layout: WorkspaceLayout,
    session_id: str | None = None,
) -> str:
    lines = [
        "ResearchHarness ready",
        f"workspace: {config.workspace_root}",
        f"research_dir: {layout.research_root}",
        f"environment_ok: {report.ok}",
    ]
    if session_id:
        lines.append(f"session_id: {session_id}")
    return "\n".join(lines)


def render_session_status(
    session: ResearchSession,
    transcript_entries: list[TranscriptEntry],
    *,
    recovery_summary: str | None = None,
) -> str:
    active_task = _resolve_active_task(session)
    active_task_summary = (
        f"{active_task.title} ({active_task.id})"
        if active_task is not None
        else (session.active_task_id or "-")
    )
    lines = [
        f"session_id: {session.id}",
        f"state: {session.state.value}",
        f"goal: {session.goal}",
        f"current_focus: {session.current_focus or '-'}",
        f"active_task: {active_task_summary}",
        f"active_task_id: {session.active_task_id or '-'}",
        f"workstream: {session.current_workstream.value}",
        f"pending_approvals: {_count_pending_approvals(session)}",
        f"plan_items: {len(session.plan_items)}",
        f"transcript_entries: {len(transcript_entries)}",
        f"updated_at: {session.updated_at.isoformat()}",
    ]
    if recovery_summary:
        lines.append(f"recovery: {recovery_summary}")
    return "\n".join(lines)


def render_command_help(commands: list[ShellCommand]) -> str:
    lines = ["Available commands:"]
    for command in commands:
        lines.append(f"{command.usage} - {command.description}")
    return "\n".join(lines)


def render_plan_view(session: ResearchSession) -> str:
    if not session.plan_items:
        return "Plan is empty."
    lines = ["Plan items:"]
    for index, item in enumerate(session.plan_items, start=1):
        lines.append(f"{index}. {item}")
    return "\n".join(lines)


def render_tasks_view(session: ResearchSession) -> str:
    if not session.tasks:
        return "No tasks yet."
    lines = ["Tasks:"]
    for task in session.tasks:
        lines.append(
            f"- [{task.status.value}] {task.title} ({task.id}) workstream={task.workstream.value} priority={task.priority}"
        )
    return "\n".join(lines)


def render_checkpoints_view(session: ResearchSession) -> str:
    if not session.checkpoints:
        return "No checkpoints yet."
    lines = ["Checkpoints:"]
    for checkpoint in session.checkpoints:
        approval_suffix = " requires_approval" if checkpoint.requires_approval else ""
        lines.append(f"- {checkpoint.summary} ({checkpoint.id}){approval_suffix}")
    return "\n".join(lines)
