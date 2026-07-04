"""Shell command tool with real-time output streaming via pseudo-TTY."""
from __future__ import annotations

import os
import pty
import re
import select
import shlex
import subprocess
import time
from pathlib import Path
from typing import Callable

from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import is_dangerous_command

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b[()][AB0]|\x1b[=>]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


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

        env = os.environ.copy()
        env["NPM_CONFIG_YES"] = "true"
        env["TERM"] = env.get("TERM", "xterm-256color")

        try:
            return self._run_pty(command, cwd, env, effective_timeout, stdin, on_output)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

    def _run_pty(
        self,
        command: str,
        cwd: Path,
        env: dict[str, str],
        timeout: int,
        stdin: str | None,
        on_output: Callable[[str], None] | None,
    ) -> ToolResult:
        master_fd, slave_fd = pty.openpty()

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=slave_fd,
                stderr=slave_fd,
                stdin=slave_fd,
                env=env,
                close_fds=True,
            )
        except Exception as e:
            os.close(master_fd)
            os.close(slave_fd)
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

        os.close(slave_fd)

        if stdin:
            try:
                os.write(master_fd, stdin.encode())
            except OSError:
                pass

        output_lines: list[str] = []
        deadline = time.time() + timeout

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                proc.kill()
                self._close_fd(master_fd)
                return ToolResult(error=f"timeout after {timeout}s", ok=False)

            try:
                rlist, _, _ = select.select([master_fd], [], [], min(remaining, 0.5))
            except (OSError, ValueError):
                break

            if rlist:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                clean = _strip_ansi(text)
                for line in clean.splitlines():
                    line = line.rstrip("\r")
                    if line.strip():
                        output_lines.append(line)
                        if on_output:
                            on_output(line)
            elif proc.poll() is not None:
                break

        self._close_fd(master_fd)
        proc.wait()

        output = "\n".join(output_lines)
        return ToolResult(
            output=output,
            error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
            ok=proc.returncode == 0,
        )

    @staticmethod
    def _close_fd(fd: int) -> None:
        try:
            os.close(fd)
        except OSError:
            pass
