"""Shell command tool."""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import is_dangerous_command


class ShellTool(Tool):
    name = "run_shell"
    description = "Run a shell command. Respects an allowlist and timeout."
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run."},
            "timeout": {"type": "integer", "description": "Timeout in seconds.", "default": 120},
            "workdir": {"type": "string", "description": "Working directory override."},
        },
        "required": ["command"],
    }

    def __init__(self, project_root: Path, allowlist: list[str] | None = None, default_timeout: int = 120):
        self.project_root = project_root
        self.allowlist = allowlist
        self.default_timeout = default_timeout

    def run(self, command: str, timeout: int | None = None, workdir: str | None = None, **_) -> ToolResult:
        bad, reason = is_dangerous_command(command)
        if bad:
            return ToolResult(error=f"blocked: {reason}", ok=False)
        if self.allowlist:
            first = shlex.split(command)[0] if command.strip() else ""
            if first not in self.allowlist:
                return ToolResult(
                    error=f"command '{first}' not in allowlist. allowed: {', '.join(self.allowlist)}",
                    ok=False,
                )
        cwd = Path(workdir) if workdir else self.project_root
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout or self.default_timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            return ToolResult(
                output=output,
                error=None if result.returncode == 0 else f"exit code {result.returncode}",
                ok=result.returncode == 0,
            )
        except subprocess.TimeoutExpired as e:
            return ToolResult(error=f"timeout after {e.timeout}s", ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)
