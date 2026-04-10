"""Small runtime bootstrap surface for later session orchestration work."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeBootstrap:
    """Minimal bootstrap state for the future interactive runtime."""

    session_id: str | None
    message: str
