"""Minimal tool registry skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolRegistry:
    """Named tool collection used by later milestones."""

    tools: dict[str, str] = field(default_factory=dict)

    def register(self, name: str, description: str) -> None:
        self.tools[name] = description
