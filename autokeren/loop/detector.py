"""Loop detector — track errors, detect repeated failures, trigger break actions."""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorEntry:
    error: str
    tool_name: str
    error_hash: str
    timestamp: float
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopAction:
    action: str = "continue"  # continue | break
    reason: str = ""
    suggestion: str = ""
    switch_model: bool = False
    clear_context: bool = False


class LoopBreaker:
    """Detect debugging loops berdasarkan repeated errors."""

    def __init__(
        self,
        max_repeats: int = 3,
        auto_switch_model: bool = True,
        auto_clear_context: bool = False,
    ) -> None:
        self.max_repeats = max_repeats
        self.auto_switch_model = auto_switch_model
        self.auto_clear_context = auto_clear_context
        self._history: list[ErrorEntry] = []

    def track_error(
        self,
        error: str,
        tool_name: str,
        context: dict[str, Any] | None = None,
    ) -> LoopAction:
        entry = ErrorEntry(
            error=error,
            tool_name=tool_name,
            error_hash=self._hash_error(error),
            timestamp=time.time(),
            context=context or {},
        )
        self._history.append(entry)
        similar = self._count_similar_recent(entry.error_hash)
        if similar >= self.max_repeats:
            return self._break(similar, entry)
        return LoopAction(action="continue")

    def _hash_error(self, error: str) -> str:
        normalized = re.sub(r"/[^\s:]+/", "<PATH>/", error)
        normalized = re.sub(r":\d+", ":N", normalized)
        normalized = re.sub(r"line \d+", "line N", normalized)
        normalized = re.sub(
            r"\d{4}-\d{2}-\d{2}[T ]?\d{2}:\d{2}:\d{2}", "<TS>", normalized
        )
        normalized = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", normalized)
        normalized = re.sub(r"v\d+", "vN", normalized)
        normalized = normalized.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _count_similar_recent(self, error_hash: str) -> int:
        count = 0
        for entry in reversed(self._history):
            if entry.error_hash == error_hash:
                count += 1
            else:
                break
        return count

    def _break(self, repeat_count: int, entry: ErrorEntry) -> LoopAction:
        actions: list[str] = []
        if self.auto_switch_model:
            actions.append("switch model")
        if self.auto_clear_context and repeat_count >= self.max_repeats + 2:
            actions.append("clear context")
        suggestion = (
            f"⚠️ LOOP BREAKER: Error berulang {repeat_count}x berturut-turut. "
            f"Actions: {', '.join(actions) if actions else 'none'}. "
            f"Saran: coba pendekatan berbeda atau breakdown masalah jadi lebih kecil."
        )
        return LoopAction(
            action="break",
            reason=f"Loop terdeteksi: error yang sama {repeat_count}x berturut-turut",
            suggestion=suggestion,
            switch_model=self.auto_switch_model,
            clear_context=self.auto_clear_context and repeat_count >= self.max_repeats + 2,
        )

    def reset(self) -> None:
        self._history.clear()

    @property
    def history(self) -> list[ErrorEntry]:
        return list(self._history)

    def status(self) -> dict[str, Any]:
        recent_hashes = [e.error_hash for e in self._history[-10:]]
        unique = len(set(recent_hashes))
        total = len(self._history)
        return {
            "total_errors": total,
            "unique_recent": unique,
            "history": [
                {
                    "tool": e.tool_name,
                    "hash": e.error_hash,
                    "error": e.error[:100],
                }
                for e in self._history[-5:]
            ],
        }
