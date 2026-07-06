"""Git helpers."""
from __future__ import annotations

import subprocess
from pathlib import Path

from autokeren.tools.base import Tool, ToolResult


class _GitBase(Tool):
    """Mixin dasar untuk semua tool git."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

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


class GitStatusTool(_GitBase):
    name = "git_status"
    description = "Show git status for the project root."
    parameters = {"type": "object", "properties": {}, "required": []}

    def run(self, **_: object) -> ToolResult:
        return self._git(["status", "--short"])


class GitDiffTool(_GitBase):
    name = "git_diff"
    description = "Show git diff for current changes. Pass staged=true to see staged changes only."
    parameters = {
        "type": "object",
        "properties": {
            "staged": {"type": "boolean", "description": "If true, show only staged (--cached) diff."},
        },
        "required": [],
    }

    def run(self, staged: bool = False, **_: object) -> ToolResult:
        args = ["diff", "--cached"] if staged else ["diff"]
        return self._git(args)


class GitCommitTool(_GitBase):
    name = "git_commit"
    description = "Stage all changes and commit with the given message following Conventional Commits format."
    requires_permission = True
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message (use Conventional Commits: feat:, fix:, docs:, etc.)"},
        },
        "required": ["message"],
    }

    def run(self, message: str, **_: object) -> ToolResult:
        self._git(["add", "-A"])
        return self._git(["commit", "-m", message])

    def permission_desc(self, message: str = "", **_: object) -> str:
        return f"git commit: {message[:60]}"


class GitLogTool(_GitBase):
    name = "git_log"
    description = "Show recent git commit history with author, date, and message."
    parameters = {
        "type": "object",
        "properties": {
            "n": {"type": "integer", "description": "Number of recent commits to show (default: 10)."},
            "oneline": {"type": "boolean", "description": "If true, show compact one-line format."},
        },
        "required": [],
    }

    def run(self, n: int = 10, oneline: bool = False, **_: object) -> ToolResult:
        fmt = ["--oneline"] if oneline else ["--pretty=format:%h  %an  %ar  %s"]
        return self._git(["log", f"-{n}"] + fmt)


class GitBranchTool(_GitBase):
    name = "git_branch"
    description = "List, create, or switch git branches."
    requires_permission = True
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "create", "switch", "create_and_switch"],
                "description": "Action to perform on branches.",
            },
            "name": {"type": "string", "description": "Branch name (required for create/switch)."},
        },
        "required": ["action"],
    }

    def run(self, action: str, name: str = "", **_: object) -> ToolResult:
        if action == "list":
            return self._git(["branch", "-a"])
        if action == "create":
            if not name:
                return ToolResult(error="Branch name required.", ok=False)
            return self._git(["branch", name])
        if action == "switch":
            if not name:
                return ToolResult(error="Branch name required.", ok=False)
            return self._git(["checkout", name])
        if action == "create_and_switch":
            if not name:
                return ToolResult(error="Branch name required.", ok=False)
            return self._git(["checkout", "-b", name])
        return ToolResult(error=f"Unknown action: {action}", ok=False)

    def permission_desc(self, action: str = "", name: str = "", **_: object) -> str:
        return f"git branch {action} {name}".strip()

    def needs_permission(self, action: str = "", **_: object) -> bool:
        return action != "list"

