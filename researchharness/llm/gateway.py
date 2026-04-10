"""LLM configuration placeholders."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMGatewayConfig:
    provider: str = "mock"
    model: str = "dummy-model"
