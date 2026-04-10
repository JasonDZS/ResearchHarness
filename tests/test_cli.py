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
            sessions_dir = Path(tmp_dir) / ".research" / "session" / "sessions"
            self.assertEqual(len(list(sessions_dir.glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
