"""MCP (Model Context Protocol) client for autokeren."""
from __future__ import annotations

import json
import subprocess
import threading
from typing import Any


class MCPError(Exception):
    pass


class MCPClient:
    """JSON-RPC 2.0 client yang berkomunikasi dengan MCP server via stdio."""

    def __init__(self, name: str, command: list[str], env: dict[str, str] | None = None) -> None:
        self.name = name
        self._command = command
        self._env = env
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._next_id = 1
        self._tools: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        import os
        merged_env = {**os.environ, **(self._env or {})}
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=merged_env,
        )
        self._initialize()
        self._tools = self._list_tools()

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ------------------------------------------------------------------
    # RPC helpers
    # ------------------------------------------------------------------

    def _send(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            raise MCPError(f"MCP server '{self.name}' is not running.")
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
            if params is not None:
                payload["params"] = params
            try:
                self._proc.stdin.write(json.dumps(payload) + "\n")
                self._proc.stdin.flush()
                raw = self._proc.stdout.readline()
            except OSError as e:
                raise MCPError(f"IO error with MCP server '{self.name}': {e}") from e
            if not raw:
                raise MCPError(f"MCP server '{self.name}' returned empty response.")
            resp = json.loads(raw)
            if "error" in resp:
                raise MCPError(f"MCP '{self.name}' error: {resp['error'].get('message', resp['error'])}")
            return resp.get("result")

    def _initialize(self) -> None:
        self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "autokeren", "version": "0.6.0"},
        })
        self._send("notifications/initialized")

    def _list_tools(self) -> list[dict[str, Any]]:
        result = self._send("tools/list")
        if isinstance(result, dict):
            return result.get("tools", [])
        return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tools(self) -> list[dict[str, Any]]:
        """Kembalikan daftar tool yang tersedia dari MCP server."""
        return self._tools

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Panggil sebuah tool di MCP server dan kembalikan outputnya."""
        result = self._send("tools/call", {"name": tool_name, "arguments": arguments})
        if isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list):
                return "\n".join(
                    c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
                )
            return str(content)
        return str(result)
