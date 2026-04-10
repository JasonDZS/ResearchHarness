from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from researchharness.cli import main
from researchharness.domain import Checkpoint, ResearchSession, Task, TaskStatus, Workstream
from researchharness.persistence import SessionStore, WorkspaceLayout
from researchharness.shell.commands import ShellCommandRegistry
from researchharness.shell.input_normalizer import combine_input_tokens, normalize_input


class InputNormalizerTests(unittest.TestCase):
    def test_normalize_shell_command(self) -> None:
        normalized = normalize_input("/status")
        self.assertEqual(normalized.kind, "shell_command")
        self.assertEqual(normalized.command_name, "status")

    def test_normalize_natural_language(self) -> None:
        normalized = normalize_input("find more 2024 papers")
        self.assertEqual(normalized.kind, "natural_language")
        self.assertEqual(normalized.text, "find more 2024 papers")

    def test_combine_input_tokens_preserves_sentence(self) -> None:
        self.assertEqual(
            combine_input_tokens(["Find", "more", "2024", "papers"]),
            "Find more 2024 papers",
        )


class ShellCommandRegistryTests(unittest.TestCase):
    def test_help_lists_builtin_commands(self) -> None:
        output = ShellCommandRegistry().execute("help", None, None, [])
        self.assertIn("/help", output)
        self.assertIn("/status", output)
        self.assertIn("/plan", output)
        self.assertIn("/tasks", output)
        self.assertIn("/checkpoint", output)


class ShellCommandSmokeTests(unittest.TestCase):
    def test_slash_commands_render_runtime_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            layout = WorkspaceLayout.from_workspace_root(workspace).ensure()
            store = SessionStore(layout)
            session = ResearchSession(
                id="session-1",
                goal="Investigate speculative decoding",
                workspace_root=str(workspace),
                current_workstream=Workstream.LITERATURE,
                current_focus="Review the reading list",
                active_task_id="task-1",
                plan_items=["Collect papers", "Draft synthesis"],
                tasks=[
                    Task(
                        id="task-1",
                        title="Collect papers",
                        status=TaskStatus.IN_PROGRESS,
                        workstream=Workstream.LITERATURE,
                    )
                ],
                checkpoints=[
                    Checkpoint(
                        id="cp-1",
                        summary="Need approval before overwriting literature notes",
                        requires_approval=True,
                    )
                ],
            )
            store.save(session)

            status_buffer = io.StringIO()
            with redirect_stdout(status_buffer):
                status_code = main(["--workspace", tmp_dir, "/status"])
            status_output = status_buffer.getvalue()
            self.assertEqual(status_code, 0)
            self.assertIn("state: active", status_output)
            self.assertIn("active_task: Collect papers (task-1)", status_output)
            self.assertIn("workstream: literature", status_output)
            self.assertIn("pending_approvals: 1", status_output)

            plan_buffer = io.StringIO()
            with redirect_stdout(plan_buffer):
                plan_code = main(["--workspace", tmp_dir, "/plan"])
            self.assertEqual(plan_code, 0)
            self.assertIn("1. Collect papers", plan_buffer.getvalue())

            tasks_buffer = io.StringIO()
            with redirect_stdout(tasks_buffer):
                tasks_code = main(["--workspace", tmp_dir, "/tasks"])
            self.assertEqual(tasks_code, 0)
            self.assertIn("[in_progress] Collect papers", tasks_buffer.getvalue())

            checkpoints_buffer = io.StringIO()
            with redirect_stdout(checkpoints_buffer):
                checkpoint_code = main(["--workspace", tmp_dir, "/checkpoint"])
            self.assertEqual(checkpoint_code, 0)
            self.assertIn("Need approval before overwriting literature notes", checkpoints_buffer.getvalue())

    def test_checkpoint_command_can_create_manual_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(["--workspace", tmp_dir, "Investigate prompt caching"])
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["--workspace", tmp_dir, "/checkpoint", "Save", "progress"])
            self.assertEqual(exit_code, 0)
            self.assertIn("Save progress", output.getvalue())

    def test_natural_language_input_continues_existing_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(["--workspace", tmp_dir, "Investigate prompt caching"])
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["--workspace", tmp_dir, "Find", "more", "2024", "papers"])
            self.assertEqual(exit_code, 0)
            self.assertIn("Recorded natural-language request", output.getvalue())

            layout = WorkspaceLayout.from_workspace_root(Path(tmp_dir)).ensure()
            store = SessionStore(layout)
            session = store.load_latest()
            self.assertIsNotNone(session)
            assert session is not None
            transcript = store.load_transcript(session.id)
            self.assertEqual(transcript[-1].event, "user_message")
            self.assertEqual(transcript[-1].message, "Find more 2024 papers")


if __name__ == "__main__":
    unittest.main()
