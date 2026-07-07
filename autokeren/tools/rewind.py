"""Rewind tool — undo N tool call terakhir via checkpoint system."""
from __future__ import annotations

from typing import Any

from autokeren.checkpoints.manager import CheckpointManager
from autokeren.tools.base import Tool, ToolResult


class RewindTool(Tool):
    name = "rewind"
    description = (
        "Undo N tool call terakhir. Restore file state ke checkpoint sebelumnya. "
        "Gunakan setelah agent ngerusak codebase atau mau coba pendekatan berbeda."
    )
    parameters = {
        "type": "object",
        "properties": {
            "steps": {
                "type": "integer",
                "description": "Jumlah tool call yang di-undo (default: 1)",
                "default": 1,
            },
        },
    }

    def __init__(self, manager: CheckpointManager) -> None:
        self.manager = manager

    def run(self, steps: int = 1, **_: Any) -> ToolResult:
        total = self.manager.count()
        if total == 0:
            return ToolResult(output="Tidak ada checkpoint untuk di-rewind.")
        actual = min(steps, total)
        undone = self.manager.rewind(actual)
        if not undone:
            return ToolResult(output="Tidak ada checkpoint untuk di-rewind.")
        lines = [f"⏪ Rewind {len(undone)} tool call:\n"]
        for cp in undone:
            tool = cp.tool_name
            arg_path = cp.tool_args.get("path", cp.tool_args.get("query", ""))
            n_changes = len(cp.file_changes)
            lines.append(f"  #{cp.id} {tool}({arg_path}) — {n_changes} file di-revert")
        remaining = self.manager.count()
        lines.append(f"\nCheckpoint tersisa: {remaining}.")
        return ToolResult(output="\n".join(lines))
