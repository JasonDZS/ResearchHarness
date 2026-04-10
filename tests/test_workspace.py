from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from researchharness.domain import Workstream
from researchharness.persistence import WorkspaceLayout


class WorkspaceTests(unittest.TestCase):
    def test_workspace_layout_creates_required_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            layout = WorkspaceLayout.from_workspace_root(workspace).ensure()

            self.assertTrue(layout.research_root.exists())
            self.assertTrue(layout.session_root.exists())
            self.assertTrue(layout.sessions_dir.exists())
            self.assertTrue(layout.transcripts_dir.exists())
            self.assertTrue(layout.artifacts_root.exists())
            for workstream in Workstream:
                self.assertTrue((layout.artifacts_root / workstream.value).exists())


if __name__ == "__main__":
    unittest.main()

