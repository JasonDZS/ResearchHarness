"""Artifact storage helpers."""

from __future__ import annotations

from pathlib import Path

from ..domain import Workstream
from ..persistence.workspace import WorkspaceLayout


def artifact_directory_for(layout: WorkspaceLayout, workstream: Workstream) -> Path:
    return layout.artifacts_root / workstream.value

