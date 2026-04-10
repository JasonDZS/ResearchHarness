from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from researchharness.cli import main
from researchharness.persistence import SessionStore, WorkspaceLayout


class ReplShellTests(unittest.TestCase):
    def test_rh_without_input_parts_enters_repl_and_creates_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = io.StringIO()
            exit_code = main(
                ["--workspace", tmp_dir],
                input_stream=io.StringIO("Investigate speculative decoding\n/exit\n"),
                output_stream=output,
            )
            self.assertEqual(exit_code, 0)
            rendered = output.getvalue()
            self.assertIn("No active session. Enter a research goal to begin.", rendered)
            self.assertIn("goal: Investigate speculative decoding", rendered)
            self.assertIn("Shell exited.", rendered)

            layout = WorkspaceLayout.from_workspace_root(Path(tmp_dir)).ensure()
            session = SessionStore(layout).load_latest()
            self.assertIsNotNone(session)
            assert session is not None
            self.assertEqual(session.state.value, "waiting_for_user")

    def test_repl_supports_mixed_turns_and_slash_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = io.StringIO()
            exit_code = main(
                ["--workspace", tmp_dir],
                input_stream=io.StringIO(
                    "Investigate prompt caching\n/status\nFind more 2024 papers\n/plan\n/exit\n"
                ),
                output_stream=output,
            )
            self.assertEqual(exit_code, 0)
            rendered = output.getvalue()
            self.assertIn("state: active", rendered)
            self.assertIn("Recorded natural-language request in the active session.", rendered)
            self.assertIn("Plan is empty.", rendered)

            layout = WorkspaceLayout.from_workspace_root(Path(tmp_dir)).ensure()
            store = SessionStore(layout)
            session = store.load_latest()
            self.assertIsNotNone(session)
            assert session is not None
            transcript = store.load_transcript(session.id)
            self.assertEqual(transcript[-1].event, "session_waiting_for_user")
            self.assertTrue(
                any(
                    entry.event == "user_message"
                    and entry.message == "Find more 2024 papers"
                    for entry in transcript
                )
            )

    def test_repl_pause_persists_before_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = io.StringIO()
            exit_code = main(
                ["--workspace", tmp_dir],
                input_stream=io.StringIO("Investigate KV-cache compression\n/pause\n"),
                output_stream=output,
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("Shell paused.", output.getvalue())

            layout = WorkspaceLayout.from_workspace_root(Path(tmp_dir)).ensure()
            session = SessionStore(layout).load_latest()
            self.assertIsNotNone(session)
            assert session is not None
            self.assertEqual(session.state.value, "paused")

    def test_repl_bootstrap_recovers_existing_interrupted_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(["--workspace", tmp_dir, "Investigate retrieval-augmented decoding"])

            layout = WorkspaceLayout.from_workspace_root(Path(tmp_dir)).ensure()
            store = SessionStore(layout)
            session = store.load_latest()
            self.assertIsNotNone(session)
            assert session is not None

            store.mark_command_start(session, "literature_search")
            session.current_focus = "Interrupted while collecting sources"
            store.save(session)

            output = io.StringIO()
            exit_code = main(
                ["--workspace", tmp_dir],
                input_stream=io.StringIO("/exit\n"),
                output_stream=output,
            )
            self.assertEqual(exit_code, 0)
            rendered = output.getvalue()
            self.assertIn("goal: Investigate retrieval-augmented decoding", rendered)
            self.assertIn("recovery: Recovered interrupted session state after `literature_search`.", rendered)
            self.assertIn("Shell exited.", rendered)

            resumed = store.load_latest()
            self.assertIsNotNone(resumed)
            assert resumed is not None
            self.assertEqual(resumed.state.value, "waiting_for_user")


if __name__ == "__main__":
    unittest.main()
