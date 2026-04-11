"""Task persistence helpers backed by the session store."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain import ResearchSession, Task, Workstream
from .session_store import SessionStore


_UNSET = object()


@dataclass
class TaskStore:
    """Persist task state as part of the saved session snapshot."""

    session_store: SessionStore

    def load_session(self, session_id: str) -> ResearchSession:
        return self.session_store.load(session_id)

    def list_tasks(self, session_id: str) -> list[Task]:
        return list(self.load_session(session_id).tasks)

    def get_task(self, session_id: str, task_id: str) -> Task:
        session = self.load_session(session_id)
        for task in session.tasks:
            if task.id == task_id:
                return task
        raise ValueError(f"Unknown task: {task_id}")

    def save_tasks(
        self,
        session_id: str,
        tasks: list[Task],
        *,
        active_task_id: str | None | object = _UNSET,
        current_workstream: Workstream | object = _UNSET,
    ) -> ResearchSession:
        session = self.load_session(session_id)
        session.tasks = list(tasks)
        if active_task_id is not _UNSET:
            session.active_task_id = active_task_id
        if current_workstream is not _UNSET:
            session.current_workstream = current_workstream
        self.session_store.save(session)
        return session
