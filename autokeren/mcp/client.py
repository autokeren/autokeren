"""MCP (Model Context Protocol) client for autokeren."""
from __future__ import annotations

import json
import queue
import subprocess
import threading
from typing import Any

from autokeren import __version__


class MCPError(Exception):
    pass


class MCPClient:
    """JSON-RPC 2.0 client yang berkomunikasi dengan MCP server via stdio."""

    _READ_TIMEOUT = 30.0

    def __init__(self, name: str, command: list[str], env: dict[str, str] | None = None) -> None:
        self.name = name
        self._command = command
        self._env = env
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._next_id = 1
        self._tools: list[dict[str, Any]] = []
        self._stdout_q: queue.Queue[str] = queue.Queue()
        self._reader_thread: threading.Thread | None = None

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
        # Background reader thread — tidak blocking di main thread
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()
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
    # Stdout reader (background thread → queue)
    # ------------------------------------------------------------------

    def _read_stdout(self) -> None:
        """Baca stdout server di background dan masukkan ke queue."""
        if not self._proc or not self._proc.stdout:
            return
        try:
            for line in self._proc.stdout:
                self._stdout_q.put(line)
        except Exception:
            pass

    def _readline_timeout(self) -> str:
        """Baca satu baris dari queue dengan timeout."""
        try:
            return self._stdout_q.get(timeout=self._READ_TIMEOUT)
        except queue.Empty:
            raise MCPError(f"MCP server '{self.name}' tidak merespons dalam {self._READ_TIMEOUT}s")

    # ------------------------------------------------------------------
    # RPC helpers
    # ------------------------------------------------------------------

    def _send_request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Kirim JSON-RPC request (dengan id) dan tunggu response."""
        if not self._proc or not self._proc.stdin:
            raise MCPError(f"MCP server '{self.name}' is not running.")
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
            if params is not None:
                payload["params"] = params
            try:
                self._proc.stdin.write(json.dumps(payload) + "\n")
                self._proc.stdin.flush()
            except OSError as e:
                raise MCPError(f"IO error dengan MCP server '{self.name}': {e}") from e

            # Baca response (ada id matching)
            while True:
                raw = self._readline_timeout()
                if not raw.strip():
                    continue
                resp = json.loads(raw)
                # Skip notifikasi dari server (tidak punya 'id')
                if "id" not in resp:
                    continue
                if resp.get("id") != req_id:
                    continue
                if "error" in resp:
                    raise MCPError(f"MCP '{self.name}' error: {resp['error'].get('message', resp['error'])}")
                return resp.get("result")

    def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Kirim JSON-RPC notification (tanpa id, tidak ada response)."""
        if not self._proc or not self._proc.stdin:
            raise MCPError(f"MCP server '{self.name}' is not running.")
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        try:
            self._proc.stdin.write(json.dumps(payload) + "\n")
            self._proc.stdin.flush()
        except OSError as e:
            raise MCPError(f"IO error dengan MCP server '{self.name}': {e}") from e

    def _initialize(self) -> None:
        # BUG FIX: initialize adalah request (butuh response)
        result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "autokeren", "version": __version__},
        })
        # Validasi response server
        if not isinstance(result, dict):
            raise MCPError(f"MCP server '{self.name}' memberikan response initialize tidak valid.")
        # BUG FIX: notifications/initialized adalah notification (tanpa id, tanpa tunggu response)
        self._send_notification("notifications/initialized")

    def _list_tools(self) -> list[dict[str, Any]]:
        result = self._send_request("tools/list")
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
        result = self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
        if isinstance(result, dict):
            # BUG FIX: cek isError dari server
            if result.get("isError"):
                content = result.get("content", [])
                if isinstance(content, list):
                    err_text = "\n".join(
                        c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
                    )
                else:
                    err_text = str(content)
                raise MCPError(f"MCP tool '{tool_name}' mengembalikan error: {err_text}")

            content = result.get("content", [])
            if isinstance(content, list):
                return "\n".join(
                    c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
                )
            return str(content)
        return str(result)
