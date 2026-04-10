"""Rendering helpers for the lightweight v0.1 CLI bootstrap."""

from __future__ import annotations

from ..domain import ResearchSession
from ..config import EnvironmentReport, ResearchHarnessConfig
from ..persistence import TranscriptEntry
from ..persistence.workspace import WorkspaceLayout


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
    lines = [
        f"session_id: {session.id}",
        f"state: {session.state.value}",
        f"goal: {session.goal}",
        f"current_focus: {session.current_focus or '-'}",
        f"active_task_id: {session.active_task_id or '-'}",
        f"plan_items: {len(session.plan_items)}",
        f"transcript_entries: {len(transcript_entries)}",
        f"updated_at: {session.updated_at.isoformat()}",
    ]
    if recovery_summary:
        lines.append(f"recovery: {recovery_summary}")
    return "\n".join(lines)
