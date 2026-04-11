"""Internal task mutation tools for later runtime orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain import Task, TaskStatus, Workstream
from ..session import TaskPlanner
from .registry import ToolRegistry


TASK_MUTATION_TOOL_DESCRIPTIONS = {
    "task_add": "Create a persisted task for the current research session.",
    "task_focus": "Focus a persisted task and mark it in progress.",
    "task_set_status": "Update the status of a persisted task.",
    "task_reprioritize": "Adjust a persisted task priority.",
    "task_link_artifacts": "Associate artifact references with a persisted task.",
}


@dataclass
class TaskMutationTools:
    """Small tool surface the future runtime can call directly."""

    planner: TaskPlanner

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
        return self.planner.add_task(
            session_id,
            title,
            workstream=workstream,
            priority=priority,
            notes=notes,
            artifact_refs=artifact_refs,
        )

    def focus_task(self, session_id: str, task_id: str) -> Task:
        return self.planner.focus_task(session_id, task_id)

    def set_status(self, session_id: str, task_id: str, status: TaskStatus | str) -> Task:
        return self.planner.set_task_status(session_id, task_id, status)

    def reprioritize(self, session_id: str, task_id: str, priority: int) -> Task:
        return self.planner.reprioritize_task(session_id, task_id, priority)

    def link_artifacts(self, session_id: str, task_id: str, artifact_refs: list[str]) -> Task:
        return self.planner.link_artifact_refs(session_id, task_id, artifact_refs)


def register_task_mutation_tools(registry: ToolRegistry) -> ToolRegistry:
    """Register the task mutation tool names for future runtime discovery."""

    for name, description in TASK_MUTATION_TOOL_DESCRIPTIONS.items():
        registry.register(name, description)
    return registry
