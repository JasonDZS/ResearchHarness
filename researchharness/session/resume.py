"""Resume and interrupted-session recovery helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain import ResearchSession, SessionState
from ..domain.models import datetime_to_str, utc_now
from ..persistence import SessionStore


@dataclass
class ResumeResult:
    """Outcome of resolving a session for resume."""

    session: ResearchSession | None
    resumed: bool
    recovered_from_interrupt: bool = False
    recovery_summary: str | None = None


class ResumeManager:
    """Resolve resume targets and recover interrupted session metadata."""

    def __init__(self, store: SessionStore) -> None:
        self.store = store

    def resume(self, session_id: str | None = None) -> ResumeResult:
        session = self.store.load(session_id) if session_id else self.store.load_latest()
        if session is None:
            return ResumeResult(session=None, resumed=False)

        runtime = session.metadata.setdefault("runtime", {})
        recovered_from_interrupt = not runtime.get("clean_shutdown", True)
        recovery_summary: str | None = None

        if recovered_from_interrupt:
            interrupted_command = runtime.get("active_command") or runtime.get("last_command")
            recovery_summary = (
                f"Recovered interrupted session state after `{interrupted_command or 'unknown'}`."
            )
            session.metadata["recovery"] = {
                "recovered_at": datetime_to_str(utc_now()),
                "reason": "unclean_shutdown",
                "interrupted_command": interrupted_command,
                "summary": recovery_summary,
            }
            self.store.append_transcript_entry(
                session.id,
                event="session_recovered",
                message=recovery_summary,
                metadata={"interrupted_command": interrupted_command},
            )
            runtime["active_command"] = None
            runtime["clean_shutdown"] = True
            runtime["last_command"] = "resume_recovery"
            runtime["last_command_completed_at"] = datetime_to_str(utc_now())

        session.state = SessionState.ACTIVE
        self.store.save(session)
        return ResumeResult(
            session=session,
            resumed=True,
            recovered_from_interrupt=recovered_from_interrupt,
            recovery_summary=recovery_summary,
        )
