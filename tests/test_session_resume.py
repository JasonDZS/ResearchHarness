from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from researchharness.cli import main
from researchharness.persistence import SessionStore, WorkspaceLayout
from researchharness.session import ResumeManager, TaskPlanner
from researchharness.persistence import TaskStore


class SessionResumeTests(unittest.TestCase):
    def test_transcript_persistence_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            main(
                [
                    "--workspace",
                    tmp_dir,
                    "--focus",
                    "Narrow to 2024 papers",
                    "--plan-item",
                    "Collect a first reading list",
                    "--task-id",
                    "task-1",
                    "Investigate speculative decoding",
                ]
            )

            layout = WorkspaceLayout.from_workspace_root(workspace).ensure()
            store = SessionStore(layout)
            session = store.load_latest()
            self.assertIsNotNone(session)
            assert session is not None
            self.assertEqual(session.current_focus, "Narrow to 2024 papers")
            self.assertEqual(session.plan_items, ["Collect a first reading list"])
            self.assertEqual(session.active_task_id, "task-1")

            transcript = store.load_transcript(session.id)
            self.assertGreaterEqual(len(transcript), 1)
            self.assertEqual(transcript[0].event, "session_started")

    def test_pause_then_resume_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(
                [
                    "--workspace",
                    tmp_dir,
                    "--focus",
                    "Read the most recent papers",
                    "--plan-item",
                    "Search arXiv and Semantic Scholar",
                    "--task-id",
                    "task-7",
                    "Map recent work on KV-cache compression",
                ]
            )

            pause_stdout = io.StringIO()
            with redirect_stdout(pause_stdout):
                pause_code = main(["pause", "--workspace", tmp_dir])
            self.assertEqual(pause_code, 0)
            self.assertIn("state: paused", pause_stdout.getvalue())

            resume_stdout = io.StringIO()
            with redirect_stdout(resume_stdout):
                resume_code = main(["resume", "--workspace", tmp_dir])
            self.assertEqual(resume_code, 0)
            resume_output = resume_stdout.getvalue()
            self.assertIn("state: active", resume_output)
            self.assertIn("goal: Map recent work on KV-cache compression", resume_output)
            self.assertIn("current_focus: Read the most recent papers", resume_output)
            self.assertIn("active_task_id: task-7", resume_output)

    def test_interrupted_session_recovery_is_surfaced_on_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            main(["--workspace", tmp_dir, "Draft a reading plan for prompt caching"])

            layout = WorkspaceLayout.from_workspace_root(workspace).ensure()
            store = SessionStore(layout)
            session = store.load_latest()
            self.assertIsNotNone(session)
            assert session is not None

            store.mark_command_start(session, "literature_search")
            session.current_focus = "Interrupted while collecting sources"
            store.save(session)

            result = ResumeManager(store).resume()
            self.assertTrue(result.resumed)
            self.assertTrue(result.recovered_from_interrupt)
            self.assertIsNotNone(result.recovery_summary)

            resumed_session = store.load_latest()
            self.assertIsNotNone(resumed_session)
            assert resumed_session is not None
            self.assertEqual(
                resumed_session.metadata["recovery"]["reason"], "unclean_shutdown"
            )
            transcript = store.load_transcript(resumed_session.id)
            self.assertEqual(transcript[-1].event, "session_recovered")

    def test_tasks_survive_pause_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            main(["--workspace", tmp_dir, "Map recent work on KV-cache compression"])

            layout = WorkspaceLayout.from_workspace_root(workspace).ensure()
            store = SessionStore(layout)
            session = store.load_latest()
            self.assertIsNotNone(session)
            assert session is not None

            planner = TaskPlanner(TaskStore(store))
            task = planner.add_task(session.id, "Collect literature", priority=2)
            planner.focus_task(session.id, task.id)

            pause_code = main(["pause", "--workspace", tmp_dir])
            self.assertEqual(pause_code, 0)

            resume_code = main(["resume", "--workspace", tmp_dir])
            self.assertEqual(resume_code, 0)

            resumed = store.load_latest()
            self.assertIsNotNone(resumed)
            assert resumed is not None
            self.assertEqual(resumed.active_task_id, task.id)
            self.assertEqual(resumed.tasks[0].title, "Collect literature")
            self.assertEqual(resumed.tasks[0].status.value, "in_progress")


if __name__ == "__main__":
    unittest.main()
