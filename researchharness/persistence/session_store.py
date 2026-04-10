"""Session persistence helpers."""

from __future__ import annotations

from pathlib import Path

from ..domain import ResearchSession
from .json_store import read_json, write_json
from .workspace import WorkspaceLayout


class SessionStore:
    """Persist and restore sessions as JSON files under `.research/session/`."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout
        self.latest_pointer = self.layout.session_root / "latest_session.txt"

    def save(self, session: ResearchSession) -> Path:
        path = self.layout.session_path(session.id)
        write_json(path, session.to_dict())
        self.latest_pointer.write_text(session.id, encoding="utf-8")
        return path

    def load(self, session_id: str) -> ResearchSession:
        return ResearchSession.from_dict(read_json(self.layout.session_path(session_id)))

    def load_latest(self) -> ResearchSession | None:
        if not self.latest_pointer.exists():
            return None
        session_id = self.latest_pointer.read_text(encoding="utf-8").strip()
        if not session_id:
            return None
        return self.load(session_id)

