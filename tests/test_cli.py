from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from researchharness.cli import main


class CliSmokeTests(unittest.TestCase):
    def test_cli_bootstraps_workspace_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            buffer = io.StringIO()
            exit_code = None
            with redirect_stdout(buffer):
                exit_code = main(["--workspace", tmp_dir])

            output = buffer.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("ResearchHarness ready", output)
            self.assertTrue((Path(tmp_dir) / ".research" / "session").exists())
            self.assertTrue((Path(tmp_dir) / ".research" / "artifacts").exists())

    def test_cli_can_create_initial_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "--workspace",
                        tmp_dir,
                        "Summarize recent work on KV-cache compression",
                    ]
                )

            output = buffer.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("session_id:", output)
            self.assertIn("state: active", output)
            sessions_dir = Path(tmp_dir) / ".research" / "session" / "sessions"
            self.assertEqual(len(list(sessions_dir.glob("*.json"))), 1)

    def test_cli_status_reports_latest_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(
                [
                    "--workspace",
                    tmp_dir,
                    "--focus",
                    "Track system state",
                    "Summarize decoding papers",
                ]
            )
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["status", "--workspace", tmp_dir])

            output = buffer.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("goal: Summarize decoding papers", output)
            self.assertIn("current_focus: Track system state", output)


if __name__ == "__main__":
    unittest.main()
