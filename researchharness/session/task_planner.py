"""Task planning and mutation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain import Task, TaskStatus, Workstream
from ..domain.models import utc_now
from ..persistence import TaskStore


@dataclass
class TaskPlanner:
    """Create, reprioritize, and focus persisted tasks."""

    task_store: TaskStore

    def add_task(
        self,
        session_id: str,
        title: str,
        *,
        workstream: Workstream | None = None,
        priority: int = 3,
        notes: str | None = None,
        artifact_refs: list[str] | None = None,
    ) -> Task:
        session = self.task_store.load_session(session_id)
        task = Task(
            id=self._next_task_id(session.tasks),
            title=title,
            status=TaskStatus.PENDING,
            workstream=workstream or session.current_workstream,
            priority=priority,
            notes=notes,
            artifact_refs=list(artifact_refs or []),
        )
        tasks = self._sorted_tasks([*session.tasks, task])
        self.task_store.save_tasks(session_id, tasks)
        self.task_store.session_store.append_transcript_entry(
            session_id,
            event="task_added",
            message=task.title,
            metadata={"task_id": task.id},
        )
        return task

    def focus_task(self, session_id: str, task_id: str) -> Task:
        session = self.task_store.load_session(session_id)
        target = self._find_task(session.tasks, task_id)
        if target.status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}:
            raise ValueError(f"Task {task_id} cannot be focused from status `{target.status.value}`.")

        now = utc_now()
        for task in session.tasks:
            if task.id == target.id:
                task.status = TaskStatus.IN_PROGRESS
                task.updated_at = now
            elif task.id == session.active_task_id and task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.PENDING
                task.updated_at = now

        self.task_store.save_tasks(
            session_id,
            self._sorted_tasks(session.tasks),
            active_task_id=target.id,
            current_workstream=target.workstream,
        )
        self.task_store.session_store.append_transcript_entry(
            session_id,
            event="task_focused",
            message=target.title,
            metadata={"task_id": target.id},
        )
        return target

    def reprioritize_task(self, session_id: str, task_id: str, priority: int) -> Task:
        session = self.task_store.load_session(session_id)
        target = self._find_task(session.tasks, task_id)
        target.priority = priority
        target.updated_at = utc_now()
        self.task_store.save_tasks(session_id, self._sorted_tasks(session.tasks))
        self.task_store.session_store.append_transcript_entry(
            session_id,
            event="task_reprioritized",
            message=target.title,
            metadata={"task_id": target.id, "priority": priority},
        )
        return target

    def set_task_status(
        self,
        session_id: str,
        task_id: str,
        status: TaskStatus | str,
    ) -> Task:
        normalized_status = status if isinstance(status, TaskStatus) else TaskStatus(status)
        if normalized_status == TaskStatus.IN_PROGRESS:
            return self.focus_task(session_id, task_id)

        session = self.task_store.load_session(session_id)
        target = self._find_task(session.tasks, task_id)
        target.status = normalized_status
        target.updated_at = utc_now()

        active_task_id = session.active_task_id
        if active_task_id == task_id and normalized_status in {
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
        }:
            active_task_id = None

        self.task_store.save_tasks(
            session_id,
            self._sorted_tasks(session.tasks),
            active_task_id=active_task_id,
        )
        self.task_store.session_store.append_transcript_entry(
            session_id,
            event="task_status_updated",
            message=target.title,
            metadata={"task_id": target.id, "status": normalized_status.value},
        )
        return target

    def link_artifact_refs(
        self,
        session_id: str,
        task_id: str,
        artifact_refs: list[str],
    ) -> Task:
        session = self.task_store.load_session(session_id)
        target = self._find_task(session.tasks, task_id)
        target.artifact_refs = self._dedupe([*target.artifact_refs, *artifact_refs])
        target.updated_at = utc_now()
        self.task_store.save_tasks(session_id, self._sorted_tasks(session.tasks))
        self.task_store.session_store.append_transcript_entry(
            session_id,
            event="task_artifacts_linked",
            message=target.title,
            metadata={"task_id": target.id, "artifact_refs": list(target.artifact_refs)},
        )
        return target

    @staticmethod
    def _find_task(tasks: list[Task], task_id: str) -> Task:
        for task in tasks:
            if task.id == task_id:
                return task
        raise ValueError(f"Unknown task: {task_id}")

    @staticmethod
    def _next_task_id(tasks: list[Task]) -> str:
        next_number = 1
        for task in tasks:
            if not task.id.startswith("task-"):
                continue
            suffix = task.id.removeprefix("task-")
            if suffix.isdigit():
                next_number = max(next_number, int(suffix) + 1)
        return f"task-{next_number}"

    @staticmethod
    def _sorted_tasks(tasks: list[Task]) -> list[Task]:
        return sorted(tasks, key=lambda task: (task.priority, task.created_at, task.id))

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            deduped.append(value)
            seen.add(value)
        return deduped
