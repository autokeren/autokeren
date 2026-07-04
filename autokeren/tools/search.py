"""Search code with ripgrep."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from autokeren.tools.base import Tool, ToolResult


class SearchCodeTool(Tool):
    name = "search_code"
    description = "Search code with ripgrep inside the project root."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern or literal string."},
            "path": {"type": "string", "description": "Subdirectory to search in.", "default": "."},
            "file_glob": {"type": "string", "description": "File glob filter, e.g. '*.py'", "default": "*"},
            "case_sensitive": {"type": "boolean", "default": False},
        },
        "required": ["pattern"],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, pattern: str, path: str = ".", file_glob: str = "*", case_sensitive: bool = False, **_) -> ToolResult:
        target = self.project_root / path
        rg = shutil.which("rg")
        cmd = [rg or "grep", "-r"]
        if not case_sensitive:
            cmd.append("-i")
        if rg and file_glob != "*":
            cmd.extend(["-g", file_glob])
        if rg:
            cmd.extend(["-n", "--", pattern, str(target)])
        else:
            cmd.extend([pattern, str(target)])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            lines = result.stdout.splitlines()[:100]
            return ToolResult(output="\n".join(lines), error=None if result.returncode in (0, 1) else result.stderr)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)
