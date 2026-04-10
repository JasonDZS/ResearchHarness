"""Configuration loading and environment validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import sys


@dataclass
class ResearchHarnessConfig:
    """Runtime configuration derived from CLI flags and the environment."""

    workspace_root: Path
    research_dir_name: str = ".research"
    sessions_dir_name: str = "session"
    artifacts_dir_name: str = "artifacts"
    default_provider: str = "mock"
    default_model: str = "dummy-model"

    @property
    def research_root(self) -> Path:
        return self.workspace_root / self.research_dir_name


@dataclass
class EnvironmentReport:
    """Structured validation report for startup checks."""

    python_version_ok: bool
    workspace_exists: bool
    workspace_writable: bool
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.workspace_exists and self.workspace_writable


def load_config(workspace_root: str | Path | None = None) -> ResearchHarnessConfig:
    """Load configuration from the environment and explicit overrides."""

    if workspace_root is None:
        raw_workspace = os.environ.get("RESEARCHHARNESS_WORKSPACE")
        base = Path(raw_workspace).expanduser() if raw_workspace else Path.cwd()
    else:
        base = Path(workspace_root).expanduser()

    return ResearchHarnessConfig(workspace_root=base.resolve())


def validate_environment(config: ResearchHarnessConfig) -> EnvironmentReport:
    """Validate the local runtime environment for v0.1 foundation work."""

    issues: list[str] = []
    python_version_ok = sys.version_info >= (3, 11)
    if not python_version_ok:
        issues.append(
            "Python 3.11 or newer is the target runtime; continuing with reduced guarantees."
        )

    workspace_exists = config.workspace_root.exists()
    if not workspace_exists:
        try:
            config.workspace_root.mkdir(parents=True, exist_ok=True)
            workspace_exists = True
        except OSError as exc:
            issues.append(f"Workspace root could not be created: {exc}")

    workspace_writable = os.access(config.workspace_root, os.W_OK) if workspace_exists else False
    if workspace_exists and not workspace_writable:
        issues.append(f"Workspace root is not writable: {config.workspace_root}")

    return EnvironmentReport(
        python_version_ok=python_version_ok,
        workspace_exists=workspace_exists,
        workspace_writable=workspace_writable,
        issues=issues,
    )
