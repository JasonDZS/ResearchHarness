from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from researchharness.domain import (
    ArtifactRef,
    Checkpoint,
    ProvenanceRecord,
    ResearchSession,
    Task,
    TaskStatus,
    Workstream,
)
from researchharness.persistence import SessionStore, WorkspaceLayout


class DomainModelTests(unittest.TestCase):
    def test_session_round_trip_via_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            layout = WorkspaceLayout.from_workspace_root(workspace).ensure()
            store = SessionStore(layout)

            session = ResearchSession(
                id="session-1",
                goal="Investigate speculative decoding",
                workspace_root=str(workspace),
                active_task_id="task-1",
                current_focus="Focus on recent efficiency papers",
                tasks=[
                    Task(
                        id="task-1",
                        title="Collect recent papers",
                        status=TaskStatus.IN_PROGRESS,
                        workstream=Workstream.LITERATURE,
                        artifact_refs=["artifact-1"],
                    )
                ],
                checkpoints=[
                    Checkpoint(
                        id="checkpoint-1",
                        summary="Initial literature sweep completed",
                        artifact_refs=["artifact-1"],
                    )
                ],
                artifacts=[
                    ArtifactRef(
                        id="artifact-1",
                        path=".research/artifacts/literature/reading-list.md",
                        workstream=Workstream.LITERATURE,
                        title="Reading list",
                    )
                ],
                provenance_records=[
                    ProvenanceRecord(
                        id="prov-1",
                        artifact_id="artifact-1",
                        source_type="paper",
                        source_id="arxiv:2301.00001",
                        citation_text="Example et al. 2023",
                    )
                ],
                transcript_path=str(layout.transcript_path("session-1")),
            )

            store.save(session)
            restored = store.load("session-1")

            self.assertEqual(restored.goal, session.goal)
            self.assertEqual(restored.active_task_id, "task-1")
            self.assertEqual(restored.tasks[0].status, TaskStatus.IN_PROGRESS)
            self.assertEqual(restored.artifacts[0].workstream, Workstream.LITERATURE)
            self.assertEqual(
                restored.provenance_records[0].source_id, "arxiv:2301.00001"
            )

    def test_invalid_task_priority_raises(self) -> None:
        with self.assertRaises(ValueError):
            Task(id="task-1", title="Bad priority", priority=-1)


if __name__ == "__main__":
    unittest.main()

