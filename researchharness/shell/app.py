"""Rendering helpers for the lightweight v0.1 CLI bootstrap."""

from __future__ import annotations

from ..config import EnvironmentReport, ResearchHarnessConfig
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

