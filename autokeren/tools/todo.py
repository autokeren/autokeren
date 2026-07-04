"""Todo list tool untuk track multi-step tasks."""
from __future__ import annotations


from autokeren.tools.base import Tool, ToolResult


class TodoTool(Tool):
    name = "todo"
    description = (
        "Kelola todo list untuk track tasks multi-step. "
        "Action: add (tambah todo), update (ubah status), list (lihat semua), clear (hapus semua)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "update", "list", "clear"],
                "description": "Aksi todo.",
            },
            "content": {"type": "string", "description": "Isi todo (untuk add)."},
            "index": {"type": "integer", "description": "Index todo (1-based, untuk update)."},
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "completed"],
                "description": "Status baru (untuk update).",
            },
        },
        "required": ["action"],
    }

    def __init__(self) -> None:
        self._todos: list[dict[str, str]] = []

    def run(self, action: str, content: str = "", index: int = 0, status: str = "pending", **_) -> ToolResult:
        try:
            if action == "add":
                if not content:
                    return ToolResult(error="content wajib untuk add", ok=False)
                self._todos.append({"content": content, "status": "pending"})
                return ToolResult(output=self._format_list())

            if action == "update":
                if index < 1 or index > len(self._todos):
                    return ToolResult(error=f"index {index} tidak valid (1-{len(self._todos)})", ok=False)
                self._todos[index - 1]["status"] = status
                return ToolResult(output=self._format_list())

            if action == "list":
                return ToolResult(output=self._format_list())

            if action == "clear":
                self._todos.clear()
                return ToolResult(output="todo list dikosongkan")

            return ToolResult(error=f"action tidak dikenal: {action}", ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

    def get_todos(self) -> list[dict[str, str]]:
        return list(self._todos)

    def _format_list(self) -> str:
        if not self._todos:
            return "todo list kosong"
        icons = {"pending": "○", "in_progress": "◐", "completed": "●"}
        lines = []
        for i, t in enumerate(self._todos, 1):
            icon = icons.get(t.get("status", "pending"), "○")
            lines.append(f"{i}. {icon} {t['content']} [{t.get('status', 'pending')}]")
        return "\n".join(lines)
