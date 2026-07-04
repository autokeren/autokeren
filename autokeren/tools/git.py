"""Git helpers."""
from __future__ import annotations

import subprocess
from pathlib import Path

from autokeren.tools.base import Tool, ToolResult


class GitStatusTool(Tool):
    name = "git_status"
    description = "Show git status for the project root."
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, **_) -> ToolResult:
        return self._git(["status", "--short"])

    def _git(self, args: list[str]) -> ToolResult:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project_root)] + args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return ToolResult(output=result.stdout, error=result.stderr or None, ok=result.returncode == 0)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Show git diff for current changes."
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, **_) -> ToolResult:
        return self._git(["diff"])

    def _git(self, args: list[str]) -> ToolResult:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project_root)] + args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return ToolResult(output=result.stdout, error=result.stderr or None, ok=result.returncode == 0)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)


class GitCommitTool(Tool):
    name = "git_commit"
    description = "Stage and commit all changes with a message."
    requires_permission = True
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message."},
        },
        "required": ["message"],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, message: str, **_) -> ToolResult:
        self._git(["add", "-A"])
        return self._git(["commit", "-m", message])

    def permission_desc(self, message: str = "", **_) -> str:
        return f"git commit: {message[:60]}"

    def _git(self, args: list[str]) -> ToolResult:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project_root)] + args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return ToolResult(output=result.stdout, error=result.stderr or None, ok=result.returncode == 0)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)
