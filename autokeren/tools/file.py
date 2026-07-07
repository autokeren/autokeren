"""File system tools."""
from __future__ import annotations

from pathlib import Path

from autokeren.security import is_sensitive_read_path, is_sensitive_write_path
from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import make_backup

try:
    import autokeren.signing as _signing
    _HAS_SIGNING = True
except ImportError:
    _HAS_SIGNING = False


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read text from a file with optional offset/limit."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative or absolute file path."},
            "offset": {"type": "integer", "description": "1-indexed starting line.", "default": 1},
            "limit": {"type": "integer", "description": "Max lines to read.", "default": 500},
        },
        "required": ["path"],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, path: str, offset: int = 1, limit: int = 500, **_) -> ToolResult:
        target = self._resolve(path)
        blocked, reason = is_sensitive_read_path(target)
        if blocked:
            return ToolResult(error=reason, ok=False)
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
    requires_permission = True
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
        blocked, reason = is_sensitive_write_path(target)
        if blocked:
            return ToolResult(error=reason, ok=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        bak = make_backup(target) if target.exists() else None
        try:
            if _HAS_SIGNING:
                if not _signing.check_signed(str(target), content):
                    content = _signing.sign_content(path, content)
            target.write_text(content, encoding="utf-8")
            lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            return ToolResult(output={
                "path": str(target),
                "lines": lines,
                "backup": str(bak) if bak else None,
                "content": content,
            })
        except Exception as e:
            return ToolResult(error=str(e), ok=False)

    def permission_desc(self, path: str = "", content: str = "", **_) -> str:
        return f"menulis/timpa file {path} ({len(content)} chars)"

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p


class PatchFileTool(Tool):
    name = "patch_file"
    description = "Replace a unique string inside a file with a new string."
    requires_permission = True
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
        blocked, reason = is_sensitive_write_path(target)
        if blocked:
            return ToolResult(error=reason, ok=False)
        if not target.exists():
            return ToolResult(error=f"file not found: {path}", ok=False)
        try:
            text = target.read_text(encoding="utf-8")
            if old_string not in text:
                return ToolResult(error="old_string not found", ok=False)
            if text.count(old_string) > 1:
                return ToolResult(error="old_string appears more than once; use a more specific chunk", ok=False)
            
            # Hitung line number awal (1-indexed) dan ambil konteks
            offset = text.index(old_string)
            lines_before = text[:offset].splitlines()
            start_line = len(lines_before) + 1

            all_lines = text.splitlines()
            context_before_idx = max(0, len(lines_before) - 2)
            context_before = all_lines[context_before_idx:len(lines_before)]

            old_lines_count = len(old_string.splitlines())
            context_after_idx = len(lines_before) + old_lines_count
            context_after = all_lines[context_after_idx:context_after_idx + 2]

            bak = make_backup(target)
            text = text.replace(old_string, new_string, 1)
            target.write_text(text, encoding="utf-8")
            return ToolResult(output={
                "path": str(target),
                "backup": str(bak) if bak else None,
                "start_line": start_line,
                "context_before": context_before,
                "context_after": context_after,
                "old_string": old_string,
                "new_string": new_string,
            })
        except Exception as e:
            return ToolResult(error=str(e), ok=False)

    def permission_desc(self, path: str = "", old_string: str = "", new_string: str = "", **_) -> str:
        return f"edit file {path}"

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p


_IGNORED_DIRS = frozenset({
    ".git", ".svn", ".hg",
    ".venv", "venv", "env", ".env",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "node_modules", ".next", ".nuxt", ".turbo",
    "build", "dist", ".eggs", "*.egg-info",
    ".tox", "htmlcov", ".coverage",
    ".idea", ".vscode",
})

_MAX_LIST_FILES = 500


class ListFilesTool(Tool):
    name = "list_files"
    description = "List files in a directory. Auto-excludes .git, .venv, node_modules, __pycache__, dll."
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
            out: list[str] = []
            if recursive:
                for p in sorted(target.rglob("*")):
                    rel = p.relative_to(self.project_root)
                    if any(part in _IGNORED_DIRS for part in rel.parts):
                        continue
                    suffix = " [dir]" if p.is_dir() else ""
                    out.append(f"{rel}{suffix}")
                    if len(out) >= _MAX_LIST_FILES:
                        out.append(f"... dipotong di {_MAX_LIST_FILES} file. Gunakan path lebih spesifik.")
                        break
            else:
                for p in sorted(target.iterdir()):
                    if p.name in _IGNORED_DIRS:
                        continue
                    suffix = " [dir]" if p.is_dir() else ""
                    out.append(f"{p.relative_to(self.project_root)}{suffix}")
            return ToolResult(output="\n".join(out))
        except Exception as e:
            return ToolResult(error=str(e), ok=False)

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.project_root / p
