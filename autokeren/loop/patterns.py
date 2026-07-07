"""Pattern detector — detect behavioral patterns beyond simple error repetition."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_APOLOGY_PATTERNS = [
    r"let me try (a different|another)",
    r"now i understand",
    r"ah,? i see",
    r"the issue is (actually|that)",
    r"let me fix this (properly|correctly)",
    r"i apologize",
    r"sorry,? let me",
    r"i see the (problem|issue)",
    r"that should (now|fix)",
]


@dataclass
class ToolCallEntry:
    name: str
    args: dict[str, Any]
    success: bool
    message: str = ""


@dataclass
class PatternResult:
    pattern: str = ""
    detected: bool = False
    detail: str = ""


class PatternDetector:
    """Detect repetitive behavioral patterns di agent tool calls."""

    def __init__(self) -> None:
        self._entries: list[ToolCallEntry] = []

    def track(self, entry: ToolCallEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > 100:
            self._entries = self._entries[-50:]

    def detect(self) -> PatternResult:
        if len(self._entries) < 3:
            return PatternResult()
        result = self._check_apology_loop()
        if result.detected:
            return result
        result = self._check_write_test_fail_cycle()
        if result.detected:
            return result
        result = self._check_same_tool_same_args()
        if result.detected:
            return result
        result = self._check_file_thrashing()
        if result.detected:
            return result
        return PatternResult()

    def _check_same_tool_same_args(self, n: int = 3) -> PatternResult:
        if len(self._entries) < n:
            return PatternResult()
        recent = self._entries[-n:]
        first = recent[0]
        for entry in recent[1:]:
            if entry.name != first.name or entry.args != first.args:
                return PatternResult()
        return PatternResult(
            pattern="same_tool_same_args",
            detected=True,
            detail=f"Tool '{first.name}' dipanggil {n}x dengan args yang sama",
        )

    def _check_write_test_fail_cycle(self, n: int = 1) -> PatternResult:
        if len(self._entries) < n * 3:
            return PatternResult()
        for i in range(len(self._entries) - n * 3 + 1):
            cycle = self._entries[i : i + 3]
            is_cycle = (
                cycle[0].name in ("write_file", "patch_file")
                and cycle[1].name in ("run_shell", "shell")
                and not cycle[1].success
                and cycle[2].name in ("write_file", "patch_file")
            )
            if is_cycle:
                return PatternResult(
                    pattern="write_test_fail_cycle",
                    detected=True,
                    detail="Write → test → fail → write cycle terdeteksi",
                )
        return PatternResult()

    def _check_file_thrashing(self, n: int = 4) -> PatternResult:
        if len(self._entries) < n:
            return PatternResult()
        recent = self._entries[-n:]
        paths: list[str] = []
        for entry in recent:
            p = entry.args.get("path", "")
            if p:
                paths.append(p)
        if len(paths) < n:
            return PatternResult()
        unique = set(paths)
        if len(unique) <= 2 and len(paths) >= 4:
            return PatternResult(
                pattern="file_thrashing",
                detected=True,
                detail=f"Bolak-balik baca/tulis file: {unique}",
            )
        return PatternResult()

    def _check_apology_loop(self, n: int = 3) -> PatternResult:
        if len(self._entries) < n:
            return PatternResult()
        recent = self._entries[-n * 2 :]
        apology_count = 0
        for entry in recent:
            if not entry.message:
                continue
            msg_lower = entry.message.lower()
            for pattern in _APOLOGY_PATTERNS:
                if re.search(pattern, msg_lower):
                    apology_count += 1
                    break
        if apology_count >= n:
            return PatternResult(
                pattern="apology_loop",
                detected=True,
                detail=f"Agent mengulang apology/realization {apology_count}x tanpa progress",
            )
        return PatternResult()

    def reset(self) -> None:
        self._entries.clear()

    @property
    def entries(self) -> list[ToolCallEntry]:
        return list(self._entries)
