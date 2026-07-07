"""Agent context / memory management."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autokeren.models.base import Message, ModelResponse, TokenUsage

_MAX_TOOL_RESULT_CHARS = 20000


@dataclass
class SessionContext:
    project_root: Path
    messages: list[Message] = field(default_factory=list)
    usage_total: TokenUsage = field(default_factory=TokenUsage)

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, response: ModelResponse) -> None:
        msg: Message = {"role": "assistant", "content": response.content or ""}
        if response.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in response.tool_calls
            ]
        self.messages.append(msg)
        self.usage_total = self.usage_total + response.usage

    def add_tool_result(self, tool_call_id: str, name: str, result: Any, ok: bool) -> None:
        content = json.dumps({"ok": ok, "result": result}, default=str)
        if len(content) > _MAX_TOOL_RESULT_CHARS:
            content = content[:_MAX_TOOL_RESULT_CHARS] + f'\n... dipotong dari {len(content)} chars'
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })

    def reset(self) -> None:
        self.messages = []
        self.usage_total = TokenUsage()

    def estimate_tokens(self) -> int:
        """Estimasi token count untuk semua messages (heuristic: chars/4)."""
        total = 0
        for msg in self.messages:
            content = str(msg.get("content", ""))
            total += len(content) // 4
            if msg.get("tool_calls"):
                total += len(json.dumps(msg["tool_calls"], default=str)) // 4
        return total

    def summary(self) -> dict[str, Any]:
        return {
            "messages": len(self.messages),
            "tokens_estimated": self.estimate_tokens(),
            "usage": {
                "prompt": self.usage_total.prompt,
                "completion": self.usage_total.completion,
                "total": self.usage_total.total,
            },
        }
