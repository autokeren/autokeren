"""Shell command tool with real-time output streaming via pseudo-TTY (Unix) or subprocess (Windows)."""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import is_dangerous_command

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b[()][AB0]|\x1b[=>]")

_IS_WINDOWS = sys.platform == "win32"

if not _IS_WINDOWS:
    import pty  # type: ignore[assignment]
    import select  # type: ignore[assignment]


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

    def run(self, command: str, timeout: int | None = None, workdir: str | None = None, stdin: str | None = None, on_output: Callable[[str], None] | None = None, check_interrupt: Callable[[], None] | None = None, **_) -> ToolResult:
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
            cwd_resolved = cwd.resolve()
            root_resolved = Path(self.project_root).resolve()
            if not cwd_resolved.is_relative_to(root_resolved):
                return ToolResult(
                    error=f"blocked: workdir '{workdir}' is outside project root",
                    ok=False,
                )
        except (OSError, ValueError):
            return ToolResult(error=f"blocked: invalid workdir '{workdir}'", ok=False)
        effective_timeout = timeout or self.default_timeout

        env = os.environ.copy()
        env["NPM_CONFIG_YES"] = "true"
        env["TERM"] = env.get("TERM", "xterm-256color")
        env["GIT_PAGER"] = "cat"
        env["PAGER"] = "cat"

        try:
            if _IS_WINDOWS:
                return self._run_subprocess(command, cwd, env, effective_timeout, stdin, on_output, check_interrupt)
            return self._run_pty(command, cwd, env, effective_timeout, stdin, on_output, check_interrupt)
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
        check_interrupt: Callable[[], None] | None,
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

        try:
            while True:
                if check_interrupt:
                    check_interrupt()
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
        except KeyboardInterrupt:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
            self._close_fd(master_fd)
            raise

        self._close_fd(master_fd)
        proc.wait()

        output = "\n".join(output_lines)
        return ToolResult(
            output=output,
            error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
            ok=proc.returncode == 0,
        )

    def _run_subprocess(
        self,
        command: str,
        cwd: Path,
        env: dict[str, str],
        timeout: int,
        stdin: str | None,
        on_output: Callable[[str], None] | None,
        check_interrupt: Callable[[], None] | None,
    ) -> ToolResult:
        """Windows fallback: pakai subprocess.Popen tanpa PTY."""
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        if stdin and proc.stdin:
            try:
                proc.stdin.write(stdin)
                proc.stdin.flush()
            except (OSError, BrokenPipeError):
                pass
            if proc.stdin:
                proc.stdin.close()

        output_lines: list[str] = []
        deadline = time.time() + timeout

        assert proc.stdout is not None
        try:
            while True:
                if check_interrupt:
                    check_interrupt()
                if time.time() > deadline:
                    proc.kill()
                    return ToolResult(error=f"timeout after {timeout}s", ok=False)

                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue

                clean = _strip_ansi(line).rstrip("\r\n")
                if clean.strip():
                    output_lines.append(clean)
                    if on_output:
                        on_output(clean)
        except KeyboardInterrupt:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise

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
