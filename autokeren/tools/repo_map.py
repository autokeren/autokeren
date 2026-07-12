"""Codebase structure indexing tool (Repo Map)."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterator

from autokeren.tools.base import Tool, ToolResult

# Import ignored directories from file tools to keep exclusion lists synchronized
_IGNORED_PATTERNS = {
    ".git", ".svn", ".hg",
    ".venv", "venv", "env", ".env",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "node_modules", ".next", ".nuxt", ".turbo",
    "build", "dist", ".eggs", "*.egg-info",
    ".tox", "htmlcov", ".coverage",
    ".idea", ".vscode", "bin",
}


class RepoMapTool(Tool):
    name = "repo_map"
    description = "Generate a compact structural map of classes, methods, and functions across the codebase."
    parameters = {
        "type": "object",
        "properties": {
            "max_files": {"type": "integer", "description": "Maximum number of files to index.", "default": 200},
        },
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, max_files: int = 200, **_) -> ToolResult:
        try:
            files = list(self._walk_files(self.project_root))
            files = sorted(files, key=lambda p: p.relative_to(self.project_root))
            
            output = []
            count = 0
            for filepath in files:
                if count >= max_files:
                    output.append(f"\n... (truncated; indexed limit of {max_files} files)")
                    break
                
                rel_path = filepath.relative_to(self.project_root)
                summary = self._parse_file(filepath)
                if summary:
                    output.append(f"- {rel_path}\n{summary}")
                    count += 1
                else:
                    # Non-code files or empty files: just list their path
                    output.append(f"- {rel_path} (non-code / empty)")
                    count += 1
            
            return ToolResult(output="\n".join(output))
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

    def _walk_files(self, root: Path) -> Iterator[Path]:
        for path in root.iterdir():
            if path.name in _IGNORED_PATTERNS:
                continue
            if path.is_dir():
                yield from self._walk_files(path)
            elif path.is_file():
                # Ignore binary or large temporary files
                if path.suffix not in (".py", ".go", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".md", ".json", ".yaml", ".yml"):
                    continue
                yield path

    def _parse_file(self, filepath: Path) -> str:
        suffix = filepath.suffix
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                return ""
            
            if suffix == ".py":
                return self._parse_python(content)
            elif suffix == ".go":
                return self._parse_go(content)
            elif suffix in (".js", ".ts", ".jsx", ".tsx"):
                return self._parse_js_ts(content)
        except Exception:
            pass
        return ""

    def _parse_python(self, content: str) -> str:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return "  [Syntax Error]"
        
        lines: list[str] = []
        
        def format_args(args_node: ast.arguments) -> str:
            args = [a.arg for a in args_node.args]
            if args_node.vararg:
                args.append(f"*{args_node.vararg.arg}")
            if args_node.kwarg:
                args.append(f"**{args_node.kwarg.arg}")
            return ", ".join(args)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                args = format_args(node.args)
                lines.append(f"  def {prefix}{node.name}({args})")
            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
                base_str = f"({bases})" if bases else ""
                lines.append(f"  class {node.name}{base_str}:")
                for subnode in node.body:
                    if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        prefix = "async " if isinstance(subnode, ast.AsyncFunctionDef) else ""
                        args = format_args(subnode.args)
                        lines.append(f"    def {prefix}{subnode.name}({args})")
        return "\n".join(lines)

    def _parse_go(self, content: str) -> str:
        lines: list[str] = []
        # Tanda tangan package
        pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_]+)", content, re.MULTILINE)
        if pkg_match:
            lines.append(f"  package {pkg_match.group(1)}")
            
        # Regex mencari tanda tangan func
        # Contoh: func (c *Client) Start(projectRoot string) error
        func_pattern = re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\([^)]*\)[^{]*", re.MULTILINE)
        for match in func_pattern.finditer(content):
            sig = match.group(0).strip().replace("\n", " ").replace("\t", " ")
            # Rapikan spasi berlebih
            sig = re.sub(r"\s+", " ", sig)
            lines.append(f"  {sig}")
        return "\n".join(lines)

    def _parse_js_ts(self, content: str) -> str:
        lines: list[str] = []
        # Regex mencari class
        class_pattern = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([a-zA-Z0-9_]+)", re.MULTILINE)
        # Regex mencari function
        func_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\([^)]*\)", re.MULTILINE)
        # Regex mencari arrow function signatures
        arrow_pattern = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", re.MULTILINE)

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            
            c_match = class_pattern.match(line)
            if c_match:
                lines.append(f"  class {c_match.group(1)}")
                continue
                
            f_match = func_pattern.match(line)
            if f_match:
                lines.append(f"  function {f_match.group(1)}()")
                continue
                
            a_match = arrow_pattern.match(line)
            if a_match:
                lines.append(f"  const {a_match.group(1)} = () =>")
                
        return "\n".join(lines)
