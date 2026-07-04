"""Shell command tool with real-time output streaming."""
from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path
from typing import Callable

from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import is_dangerous_command


class ShellTool(Tool):
    name = "run_shell"
    description = "Run a shell command. Output streams in real-time. Respects an allowlist and timeout."
    requires_permission = True
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run."},
            "timeout": {"type": "integer", "description": "Timeout in seconds.", "default": 120},
            "workdir": {"type": "string", "description": "Working directory override."},
            "stdin": {"type": "string", "description": "Input to pipe to stdin for interactive commands. e.g. 'y\\n' to accept prompts, 'my-app\\n' to answer project name."},
        },
        "required": ["command"],
    }

    def __init__(self, project_root: Path, allowlist: list[str] | None = None, default_timeout: int = 120):
        self.project_root = project_root
        self.allowlist = allowlist
        self.default_timeout = default_timeout

    def permission_desc(self, command: str = "", **_) -> str:
        cmd_preview = command if len(command) <= 80 else command[:77] + "…"
        return f"jalankan shell: {cmd_preview}"

    def run(self, command: str, timeout: int | None = None, workdir: str | None = None, stdin: str | None = None, on_output: Callable[[str], None] | None = None, **_) -> ToolResult:
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
        effective_timeout = timeout or self.default_timeout

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                stdin=subprocess.PIPE if stdin else None,
            )
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

        output_lines: list[str] = []
        deadline = time.time() + effective_timeout

        try:
            if stdin and proc.stdin:
                proc.stdin.write(stdin)
                proc.stdin.close()

            assert proc.stdout is not None
            for line in proc.stdout:
                stripped = line.rstrip()
                output_lines.append(stripped)
                if on_output:
                    on_output(stripped)
                if time.time() > deadline:
                    proc.kill()
                    return ToolResult(error=f"timeout after {effective_timeout}s", ok=False)

            remaining = max(1, int(deadline - time.time()))
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            proc.kill()
            return ToolResult(error=f"timeout after {effective_timeout}s", ok=False)
        except Exception as e:
            proc.kill()
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

        output = "\n".join(output_lines)
        return ToolResult(
            output=output,
            error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
            ok=proc.returncode == 0,
        )
