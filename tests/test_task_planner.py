from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from researchharness.domain import ResearchSession, TaskStatus, Workstream
from researchharness.persistence import SessionStore, TaskStore, WorkspaceLayout
from researchharness.session import TaskPlanner
from researchharness.tools import TaskMutationTools, ToolRegistry, register_task_mutation_tools


class TaskPlannerTests(unittest.TestCase):
    def test_task_planner_crud_and_status_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            layout = WorkspaceLayout.from_workspace_root(workspace).ensure()
            session_store = SessionStore(layout)
            session = ResearchSession(
                id="session-1",
                goal="Investigate prompt caching",
                workspace_root=str(workspace),
            )
            session_store.save(session)

            planner = TaskPlanner(TaskStore(session_store))
            first = planner.add_task(
                session.id,
                "Collect papers",
                workstream=Workstream.LITERATURE,
                priority=2,
            )
            second = planner.add_task(
                session.id,
                "Draft synthesis",
                workstream=Workstream.WRITING,
                priority=4,
            )

            self.assertEqual(first.id, "task-1")
            self.assertEqual(second.id, "task-2")

            focused = planner.focus_task(session.id, second.id)
            self.assertEqual(focused.status, TaskStatus.IN_PROGRESS)

            reprioritized = planner.reprioritize_task(session.id, second.id, 1)
            self.assertEqual(reprioritized.priority, 1)

            linked = planner.link_artifact_refs(session.id, second.id, ["artifact-1", "artifact-1"])
            self.assertEqual(linked.artifact_refs, ["artifact-1"])

            completed = planner.set_task_status(session.id, second.id, TaskStatus.COMPLETED)
            self.assertEqual(completed.status, TaskStatus.COMPLETED)

            restored = session_store.load(session.id)
            self.assertEqual(restored.active_task_id, None)
            self.assertEqual([task.id for task in restored.tasks], ["task-2", "task-1"])
            self.assertEqual(restored.tasks[0].artifact_refs, ["artifact-1"])

    def test_task_mutation_tools_register_and_persist_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            layout = WorkspaceLayout.from_workspace_root(workspace).ensure()
            session_store = SessionStore(layout)
            session = ResearchSession(
                id="session-1",
                goal="Investigate speculative decoding",
                workspace_root=str(workspace),
            )
            session_store.save(session)

            registry = register_task_mutation_tools(ToolRegistry())
            self.assertIn("task_add", registry.tools)
            self.assertIn("task_focus", registry.tools)

            tools = TaskMutationTools(TaskPlanner(TaskStore(session_store)))
            task = tools.add_task(session.id, "Collect benchmark papers")
            tools.focus_task(session.id, task.id)
            tools.link_artifacts(session.id, task.id, ["artifact-1", "artifact-2"])
            tools.set_status(session.id, task.id, "blocked")

            restored = session_store.load(session.id)
            self.assertEqual(restored.active_task_id, task.id)
            self.assertEqual(restored.tasks[0].status, TaskStatus.BLOCKED)
            self.assertEqual(restored.tasks[0].artifact_refs, ["artifact-1", "artifact-2"])


if __name__ == "__main__":
    unittest.main()
