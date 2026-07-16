"""Tmux supervisor tool."""
from __future__ import annotations

import re
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
                "enum": ["run", "capture", "list", "kill", "exists", "sniff"],
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

    def needs_permission(self, action: str = "", **_) -> bool:
        return action in ("run", "kill")

    def permission_desc(self, action: str = "", command: str = "", session: str = "", **_) -> str:
        if action == "run":
            return f"tmux run: {command[:60]}" if command else f"tmux run di session {session}"
        return f"tmux {action} session {session}"

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
            if action == "sniff":
                target = f"{session}:{window or '0'}.{pane}"
                result = subprocess.run([self.tmux, "capture-pane", "-p", "-t", target, "-S", f"-{lines}"], capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    return ToolResult(error=result.stderr or "failed to capture pane", ok=False)
                
                output_text = result.stdout
                error_patterns = [
                    r"TypeError:.*",
                    r"ReferenceError:.*",
                    r"SyntaxError:.*",
                    r"RuntimeError:.*",
                    r"Error:.*",
                    r"Traceback \(most recent call last\):",
                    r"panic:.*",
                    r"fatal error:.*",
                    r"500 Internal Server Error",
                ]
                
                found_errors = []
                lines_list = output_text.splitlines()
                for i, line in enumerate(lines_list):
                    for pat in error_patterns:
                        if re.search(pat, line):
                            if "Traceback" in line:
                                traceback_block = lines_list[i:i+15]
                                found_errors.append("\n".join(traceback_block))
                            else:
                                found_errors.append(line)
                            break
                
                if found_errors:
                    unique_errors = list(dict.fromkeys(found_errors))
                    return ToolResult(
                        ok=False,
                        error="Detected error patterns in tmux logs.",
                        output="\n".join(unique_errors)
                    )
                return ToolResult(output="Logs are clean. No error patterns detected.", ok=True)
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
