"""Tmux supervisor tool."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from autokeren.tools.base import Tool, ToolResult


class TmuxTool(Tool):
    name = "tmux"
    description = "Manage tmux sessions for long-running tasks."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["run", "capture", "list", "kill", "exists"],
            },
            "session": {"type": "string", "default": "autokeren"},
            "command": {"type": "string"},
            "window": {"type": "string"},
            "pane": {"type": "string", "default": "0"},
            "lines": {"type": "integer", "default": 100},
        },
        "required": ["action"],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tmux = shutil.which("tmux") or "tmux"

    def run(self, action: str, session: str = "autokeren", command: str | None = None, window: str | None = None, pane: str = "0", lines: int = 100, **_) -> ToolResult:
        try:
            if action == "run":
                if not command:
                    return ToolResult(error="command required", ok=False)
                target = f"{session}:{window or '0'}"
                exists = subprocess.run([self.tmux, "has-session", "-t", session], capture_output=True).returncode == 0
                if not exists:
                    subprocess.run([self.tmux, "new-session", "-d", "-s", session, "-c", str(self.project_root)], check=True)
                if window:
                    subprocess.run([self.tmux, "new-window", "-d", "-t", session, "-n", window, "-c", str(self.project_root)], check=False)
                subprocess.run([self.tmux, "send-keys", "-t", target, command, "C-m"], check=True)
                return ToolResult(output=f"sent to tmux {target}: {command}")
            if action == "capture":
                target = f"{session}:{window or '0'}.{pane}"
                result = subprocess.run([self.tmux, "capture-pane", "-p", "-t", target, "-S", f"-{lines}"], capture_output=True, text=True, timeout=30)
                return ToolResult(output=result.stdout, error=result.stderr or None, ok=result.returncode == 0)
            if action == "list":
                result = subprocess.run([self.tmux, "list-sessions", "-F", "#{session_name}: #{session_windows} windows"], capture_output=True, text=True, timeout=30)
                return ToolResult(output=result.stdout, error=result.stderr or None, ok=result.returncode == 0)
            if action == "kill":
                result = subprocess.run([self.tmux, "kill-session", "-t", session], capture_output=True, text=True, timeout=30)
                return ToolResult(output=result.stdout or "killed", error=result.stderr or None, ok=result.returncode == 0)
            if action == "exists":
                rc = subprocess.run([self.tmux, "has-session", "-t", session], capture_output=True, timeout=10).returncode
                return ToolResult(output={"exists": rc == 0}, ok=rc == 0)
            return ToolResult(error=f"unknown tmux action: {action}", ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)
