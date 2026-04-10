"""Session persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from ..domain import ResearchSession, SessionState
from ..domain.models import datetime_from_str, datetime_to_str, utc_now
from .json_store import read_json, write_json
from .workspace import WorkspaceLayout


@dataclass
class TranscriptEntry:
    """Structured transcript row persisted as JSONL."""

    timestamp: datetime
    event: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": datetime_to_str(self.timestamp),
            "event": self.event,
            "message": self.message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptEntry":
        return cls(
            timestamp=datetime_from_str(data["timestamp"]),
            event=data["event"],
            message=data["message"],
            metadata=dict(data.get("metadata", {})),
        )


class SessionStore:
    """Persist and restore sessions as JSON files under `.research/session/`."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout
        self.latest_pointer = self.layout.session_root / "latest_session.txt"

    def save(self, session: ResearchSession) -> Path:
        if not session.transcript_path:
            session.transcript_path = str(self.layout.transcript_path(session.id))
        session.updated_at = utc_now()
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

    def append_transcript_entry(
        self,
        session_id: str,
        event: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> TranscriptEntry:
        entry = TranscriptEntry(
            timestamp=utc_now(),
            event=event,
            message=message,
            metadata=dict(metadata or {}),
        )
        transcript_path = self.layout.transcript_path(session_id)
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with transcript_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")
        return entry

    def load_transcript(self, session_id: str) -> list[TranscriptEntry]:
        transcript_path = self.layout.transcript_path(session_id)
        if not transcript_path.exists():
            return []
        entries: list[TranscriptEntry] = []
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(TranscriptEntry.from_dict(json.loads(line)))
        return entries

    def mark_command_start(self, session: ResearchSession, command_name: str) -> ResearchSession:
        runtime = self._runtime_metadata(session)
        runtime["last_command"] = command_name
        runtime["active_command"] = command_name
        runtime["last_command_started_at"] = datetime_to_str(utc_now())
        runtime["clean_shutdown"] = False
        session.state = SessionState.ACTIVE
        self.save(session)
        return session

    def mark_command_end(
        self,
        session: ResearchSession,
        command_name: str,
        *,
        safe_boundary: str | None = None,
    ) -> ResearchSession:
        runtime = self._runtime_metadata(session)
        runtime["last_command"] = command_name
        runtime["active_command"] = None
        runtime["last_command_completed_at"] = datetime_to_str(utc_now())
        runtime["clean_shutdown"] = True
        if safe_boundary:
            runtime["last_safe_boundary"] = safe_boundary
            runtime["last_safe_boundary_at"] = datetime_to_str(utc_now())
        self.save(session)
        return session

    def mark_safe_boundary(self, session: ResearchSession, summary: str) -> ResearchSession:
        self.append_transcript_entry(
            session.id,
            event="safe_boundary",
            message=summary,
        )
        runtime = self._runtime_metadata(session)
        runtime["last_safe_boundary"] = summary
        runtime["last_safe_boundary_at"] = datetime_to_str(utc_now())
        self.save(session)
        return session

    def latest_status(self) -> dict[str, Any] | None:
        session = self.load_latest()
        if session is None:
            return None
        transcript_entries = self.load_transcript(session.id)
        runtime = dict(session.metadata.get("runtime", {}))
        recovery = dict(session.metadata.get("recovery", {}))
        return {
            "session": session,
            "transcript_entries": transcript_entries,
            "runtime": runtime,
            "recovery": recovery,
        }

    @staticmethod
    def _runtime_metadata(session: ResearchSession) -> dict[str, Any]:
        runtime = session.metadata.setdefault("runtime", {})
        if "clean_shutdown" not in runtime:
            runtime["clean_shutdown"] = True
        return runtime
