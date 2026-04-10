"""Workspace layout helpers for `.research/`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..domain import Workstream


@dataclass
class WorkspaceLayout:
    """Resolved filesystem layout for a single research workspace."""

    workspace_root: Path
    research_root: Path
    session_root: Path
    sessions_dir: Path
    transcripts_dir: Path
    artifacts_root: Path

    @classmethod
    def from_workspace_root(cls, workspace_root: Path, research_dir_name: str = ".research") -> "WorkspaceLayout":
        research_root = workspace_root / research_dir_name
        session_root = research_root / "session"
        return cls(
            workspace_root=workspace_root,
            research_root=research_root,
            session_root=session_root,
            sessions_dir=session_root / "sessions",
            transcripts_dir=session_root / "transcripts",
            artifacts_root=research_root / "artifacts",
        )

    def ensure(self) -> "WorkspaceLayout":
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        for workstream in Workstream:
            self.artifacts_root.joinpath(workstream.value).mkdir(parents=True, exist_ok=True)
        return self

    def session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def transcript_path(self, session_id: str) -> Path:
        return self.transcripts_dir / f"{session_id}.log"
