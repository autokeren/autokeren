"""File system tools."""
from __future__ import annotations

from pathlib import Path

from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import make_backup


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read text from a file with optional offset/limit."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative or absolute file path."},
            "offset": {"type": "integer", "description": "1-indexed starting line.", "default": 1},
            "limit": {"type": "integer", "description": "Max lines to read.", "default": 200},
        },
        "required": ["path"],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, path: str, offset: int = 1, limit: int = 200, **_) -> ToolResult:
        target = self._resolve(path)
        if not target.exists():
            return ToolResult(error=f"file not found: {path}", ok=False)
        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            start = max(0, offset - 1)
            end = start + limit
            selected = lines[start:end]
            numbered = "\n".join(f"{i+1:4}|{ln}" for i, ln in enumerate(selected, start=start))
            return ToolResult(output={"path": str(target), "total_lines": len(lines), "content": numbered})
        except Exception as e:
            return ToolResult(error=str(e), ok=False)

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.project_root / p


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write or overwrite a file. Creates backups automatically."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, path: str, content: str, **_) -> ToolResult:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        bak = make_backup(target)
        try:
            target.write_text(content, encoding="utf-8")
            return ToolResult(output={"path": str(target), "backup": str(bak) if bak else None})
        except Exception as e:
            return ToolResult(error=str(e), ok=False)

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p


class PatchFileTool(Tool):
    name = "patch_file"
    description = "Replace a unique string inside a file with a new string."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
        },
        "required": ["path", "old_string", "new_string"],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, path: str, old_string: str, new_string: str, **_) -> ToolResult:
        target = self._resolve(path)
        if not target.exists():
            return ToolResult(error=f"file not found: {path}", ok=False)
        try:
            text = target.read_text(encoding="utf-8")
            if old_string not in text:
                return ToolResult(error="old_string not found", ok=False)
            if text.count(old_string) > 1:
                return ToolResult(error="old_string appears more than once; use a more specific chunk", ok=False)
            bak = make_backup(target)
            text = text.replace(old_string, new_string, 1)
            target.write_text(text, encoding="utf-8")
            return ToolResult(output={"path": str(target), "backup": str(bak) if bak else None})
        except Exception as e:
            return ToolResult(error=str(e), ok=False)

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p


class ListFilesTool(Tool):
    name = "list_files"
    description = "List files in a directory."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
            "recursive": {"type": "boolean", "default": False},
        },
        "required": [],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, path: str = ".", recursive: bool = False, **_) -> ToolResult:
        target = self._resolve(path)
        try:
            out = []
            if recursive:
                for p in sorted(target.rglob("*")):
                    suffix = " [dir]" if p.is_dir() else ""
                    out.append(f"{p.relative_to(self.project_root)}{suffix}")
            else:
                for p in sorted(target.iterdir()):
                    suffix = " [dir]" if p.is_dir() else ""
                    out.append(f"{p.relative_to(self.project_root)}{suffix}")
            return ToolResult(output="\n".join(out))
        except Exception as e:
            return ToolResult(error=str(e), ok=False)

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p
