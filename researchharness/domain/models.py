"""Core typed models used throughout ResearchHarness."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def datetime_to_str(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def datetime_from_str(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def _require_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


class SessionState(str, Enum):
    ACTIVE = "active"
    WAITING_FOR_USER = "waiting_for_user"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Workstream(str, Enum):
    IDEATION = "ideation"
    LITERATURE = "literature"
    EXPERIMENT_DESIGN = "experiment_design"
    ANALYSIS = "analysis"
    WRITING = "writing"


@dataclass
class ArtifactRef:
    id: str
    path: str
    workstream: Workstream
    title: str
    description: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = _require_non_empty(self.id, "ArtifactRef.id")
        self.path = _require_non_empty(self.path, "ArtifactRef.path")
        self.title = _require_non_empty(self.title, "ArtifactRef.title")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "workstream": self.workstream.value,
            "title": self.title,
            "description": self.description,
            "created_at": datetime_to_str(self.created_at),
            "updated_at": datetime_to_str(self.updated_at),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRef":
        return cls(
            id=data["id"],
            path=data["path"],
            workstream=Workstream(data["workstream"]),
            title=data["title"],
            description=data.get("description"),
            created_at=datetime_from_str(data["created_at"]),
            updated_at=datetime_from_str(data["updated_at"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ProvenanceRecord:
    id: str
    artifact_id: str
    source_type: str
    source_id: str
    citation_text: str
    locator: str | None = None
    notes: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = _require_non_empty(self.id, "ProvenanceRecord.id")
        self.artifact_id = _require_non_empty(self.artifact_id, "ProvenanceRecord.artifact_id")
        self.source_type = _require_non_empty(self.source_type, "ProvenanceRecord.source_type")
        self.source_id = _require_non_empty(self.source_id, "ProvenanceRecord.source_id")
        self.citation_text = _require_non_empty(
            self.citation_text, "ProvenanceRecord.citation_text"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "citation_text": self.citation_text,
            "locator": self.locator,
            "notes": self.notes,
            "created_at": datetime_to_str(self.created_at),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenanceRecord":
        return cls(
            id=data["id"],
            artifact_id=data["artifact_id"],
            source_type=data["source_type"],
            source_id=data["source_id"],
            citation_text=data["citation_text"],
            locator=data.get("locator"),
            notes=data.get("notes"),
            created_at=datetime_from_str(data["created_at"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class Task:
    id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    workstream: Workstream = Workstream.IDEATION
    priority: int = 3
    artifact_refs: list[str] = field(default_factory=list)
    notes: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.id = _require_non_empty(self.id, "Task.id")
        self.title = _require_non_empty(self.title, "Task.title")
        if self.priority < 0:
            raise ValueError("Task.priority must be >= 0.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "workstream": self.workstream.value,
            "priority": self.priority,
            "artifact_refs": list(self.artifact_refs),
            "notes": self.notes,
            "created_at": datetime_to_str(self.created_at),
            "updated_at": datetime_to_str(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            title=data["title"],
            status=TaskStatus(data["status"]),
            workstream=Workstream(data["workstream"]),
            priority=int(data.get("priority", 3)),
            artifact_refs=list(data.get("artifact_refs", [])),
            notes=data.get("notes"),
            created_at=datetime_from_str(data["created_at"]),
            updated_at=datetime_from_str(data["updated_at"]),
        )


@dataclass
class Checkpoint:
    id: str
    summary: str
    related_task_id: str | None = None
    artifact_refs: list[str] = field(default_factory=list)
    requires_approval: bool = False
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = _require_non_empty(self.id, "Checkpoint.id")
        self.summary = _require_non_empty(self.summary, "Checkpoint.summary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "summary": self.summary,
            "related_task_id": self.related_task_id,
            "artifact_refs": list(self.artifact_refs),
            "requires_approval": self.requires_approval,
            "created_at": datetime_to_str(self.created_at),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        return cls(
            id=data["id"],
            summary=data["summary"],
            related_task_id=data.get("related_task_id"),
            artifact_refs=list(data.get("artifact_refs", [])),
            requires_approval=bool(data.get("requires_approval", False)),
            created_at=datetime_from_str(data["created_at"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ResearchSession:
    id: str
    goal: str
    workspace_root: str
    state: SessionState = SessionState.ACTIVE
    current_focus: str | None = None
    current_workstream: Workstream = Workstream.IDEATION
    active_task_id: str | None = None
    plan_items: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    checkpoints: list[Checkpoint] = field(default_factory=list)
    artifacts: list[ArtifactRef] = field(default_factory=list)
    provenance_records: list[ProvenanceRecord] = field(default_factory=list)
    transcript_path: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = _require_non_empty(self.id, "ResearchSession.id")
        self.goal = _require_non_empty(self.goal, "ResearchSession.goal")
        self.workspace_root = _require_non_empty(
            self.workspace_root, "ResearchSession.workspace_root"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "workspace_root": self.workspace_root,
            "state": self.state.value,
            "current_focus": self.current_focus,
            "current_workstream": self.current_workstream.value,
            "active_task_id": self.active_task_id,
            "plan_items": list(self.plan_items),
            "tasks": [task.to_dict() for task in self.tasks],
            "checkpoints": [checkpoint.to_dict() for checkpoint in self.checkpoints],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "provenance_records": [
                record.to_dict() for record in self.provenance_records
            ],
            "transcript_path": self.transcript_path,
            "created_at": datetime_to_str(self.created_at),
            "updated_at": datetime_to_str(self.updated_at),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchSession":
        return cls(
            id=data["id"],
            goal=data["goal"],
            workspace_root=data["workspace_root"],
            state=SessionState(data["state"]),
            current_focus=data.get("current_focus"),
            current_workstream=Workstream(data.get("current_workstream", Workstream.IDEATION)),
            active_task_id=data.get("active_task_id"),
            plan_items=list(data.get("plan_items", [])),
            tasks=[Task.from_dict(item) for item in data.get("tasks", [])],
            checkpoints=[Checkpoint.from_dict(item) for item in data.get("checkpoints", [])],
            artifacts=[ArtifactRef.from_dict(item) for item in data.get("artifacts", [])],
            provenance_records=[
                ProvenanceRecord.from_dict(item)
                for item in data.get("provenance_records", [])
            ],
            transcript_path=data.get("transcript_path"),
            created_at=datetime_from_str(data["created_at"]),
            updated_at=datetime_from_str(data["updated_at"]),
            metadata=dict(data.get("metadata", {})),
        )
