"""Remember tool — agent bisa simpan info penting ke memory."""
from __future__ import annotations

from typing import TYPE_CHECKING

from autokeren.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from autokeren.memory import MemoryManager


class RememberTool(Tool):
    name = "remember"
    description = (
        "Simpan info penting ke memory untuk session selanjutnya. "
        "Section contoh: build, debug, preferensi, arsitektur, error. "
        "Hanya simpan hal yang berguna untuk masa depan."
    )
    parameters = {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": "Kategori memory (build, debug, preferensi, arsitektur, dll)",
            },
            "note": {"type": "string", "description": "Hal yang perlu diingat"},
        },
        "required": ["section", "note"],
    }

    def __init__(self, memory: "MemoryManager") -> None:
        self.memory = memory

    def run(self, section: str, note: str, **_) -> ToolResult:
        try:
            self.memory.append(section, note)
            count = self.memory.line_count()
            return ToolResult(output=f"tersimpan di memory [{section}]. Total: {count} baris.")
        except Exception as e:
            return ToolResult(error=str(e), ok=False)
