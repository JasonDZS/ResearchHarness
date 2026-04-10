"""Normalize shell-style commands and natural-language session input."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NormalizedInput:
    """Normalized representation of user input for the shell layer."""

    kind: str
    raw_text: str
    text: str | None = None
    command_name: str | None = None
    command_args: list[str] = field(default_factory=list)


def combine_input_tokens(parts: list[str] | None) -> str:
    if not parts:
        return ""
    return " ".join(part.strip() for part in parts if part.strip()).strip()


def normalize_input(raw_text: str) -> NormalizedInput:
    text = raw_text.strip()
    if not text:
        return NormalizedInput(kind="empty", raw_text=raw_text)

    if text.startswith("/"):
        tokens = text.split()
        command_name = tokens[0][1:]
        return NormalizedInput(
            kind="shell_command",
            raw_text=raw_text,
            command_name=command_name,
            command_args=tokens[1:],
        )

    return NormalizedInput(kind="natural_language", raw_text=raw_text, text=text)

