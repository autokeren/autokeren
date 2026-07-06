"""MCPTool: wrapper Tool untuk memanggil tool dari MCP server."""
from __future__ import annotations

from typing import Any

from autokeren.tools.base import Tool, ToolResult


class MCPTool(Tool):
    """Dinamis tool yang delegasi eksekusi ke MCP server."""

    requires_permission = True

    def __init__(self, mcp_client: Any, tool_schema: dict[str, Any]) -> None:
        self._client = mcp_client
        self._schema = tool_schema
        self.name = f"mcp__{mcp_client.name}__{tool_schema['name']}"
        server_name = mcp_client.name
        tool_name = tool_schema["name"]
        self.description = f"[MCP:{server_name}] {tool_schema.get('description', tool_name)}"
        self.parameters = tool_schema.get("inputSchema", {"type": "object", "properties": {}, "required": []})

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            output = self._client.call_tool(self._schema["name"], kwargs)
            return ToolResult(output=output, ok=True)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

    def permission_desc(self, **kwargs: Any) -> str:
        return f"MCP {self._client.name} → {self._schema['name']}({', '.join(f'{k}={v!r}' for k, v in kwargs.items())})"
