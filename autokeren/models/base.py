"""Shared model abstractions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenUsage:
    prompt: int = 0
    completion: int = 0
    total: int = 0
    cost_usd: float | None = None

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt=self.prompt + other.prompt,
            completion=self.completion + other.completion,
            total=self.total + other.total,
            cost_usd=(self.cost_usd or 0) + (other.cost_usd or 0),
        )


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    thought: str | None = None


@dataclass
class ModelResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    model_id: str = ""
    finish_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    neurons_used: int = 0
    neurons_remaining: int | None = None
    neurons_quota: int | None = None


Message = dict[str, Any]  # OpenAI-compatible message
