"""Tool abstraction and registry."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ToolResult:
    def __init__(self, output: str | dict | list | None = None, error: str | None = None, ok: bool = True):
        self.output = output
        self.error = error
        self.ok = ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
        }

    def to_string(self, max_length: int = 8000) -> str:
        text = str(self.output) if self.output else ""
        if self.error:
            text += f"\nERROR: {self.error}"
        if len(text) > max_length:
            text = text[:max_length] + f"\n... truncated from {len(text)} chars"
        return text


class Tool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}
    requires_permission: bool = False

    def needs_permission(self, *args: Any, **kwargs: Any) -> bool:
        """Override untuk dynamic permission check berdasarkan arguments."""
        return self.requires_permission

    def permission_desc(self, *args: Any, **kwargs: Any) -> str:
        """Deskripsi human-readable untuk dialog konfirmasi."""
        return self.description

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> ToolResult:
        raise NotImplementedError

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> "ToolRegistry":
        self.tools[tool.name] = tool
        return self

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self.tools.values()]

    def names(self) -> list[str]:
        return list(self.tools.keys())

    def check_permission(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Return (needs_permission, description)."""
        tool = self.get(name)
        if tool and tool.needs_permission(**arguments):
            return True, tool.permission_desc(**arguments)
        return False, ""

    def run(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(error=f"tool tidak ditemukan: {name}", ok=False)
        try:
            return tool.run(**arguments)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)
