"""Codebase structure indexing tool (Repo Map) with caching and semantic relevance filtering."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterator

from autokeren.tools.base import Tool, ToolResult

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
            "max_files": {"type": "integer", "description": "Maximum number of files to show signatures for.", "default": 15},
            "query": {"type": "string", "description": "Search query or task description to filter relevant signatures.", "default": ""},
        },
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, max_files: int = 15, query: str = "", **_) -> ToolResult:
        try:
            res = self.get_relevant_map(query, max_files=max_files)
            return ToolResult(output=res)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

    def _cache_path(self) -> Path:
        return self.project_root / ".ak-repomap.cache"

    def load_cache(self) -> dict:
        path = self._cache_path()
        if not path.exists():
            return {"files": {}}
        try:
            import json
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"files": {}}

    def save_cache(self, cache: dict) -> None:
        path = self._cache_path()
        try:
            import json
            path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        except Exception:
            pass

    def update_index(self) -> dict:
        cache = self.load_cache()
        files = list(self._walk_files(self.project_root))
        
        existing_rel_paths = {str(p.relative_to(self.project_root)) for p in files}
        cache_files = cache.setdefault("files", {})
        for cached_rel_path in list(cache_files.keys()):
            if cached_rel_path not in existing_rel_paths:
                del cache_files[cached_rel_path]
                
        for filepath in files:
            rel_path = str(filepath.relative_to(self.project_root))
            try:
                mtime = filepath.stat().st_mtime
            except OSError:
                continue
                
            cached = cache_files.get(rel_path)
            if not cached or cached.get("mtime") != mtime:
                summary, symbols = self._parse_file(filepath)
                cache_files[rel_path] = {
                    "mtime": mtime,
                    "summary": summary,
                    "symbols": symbols,
                }
        self.save_cache(cache)
        return cache

    def get_relevant_map(self, query: str, max_files: int = 15) -> str:
        cache = self.update_index()
        cache_files = cache.get("files", {})
        
        keywords = [w.lower() for w in re.findall(r"[a-zA-Z0-9_]{3,}", query)]
        if not keywords:
            output = []
            for rel_path, info in sorted(cache_files.items()):
                summary = info.get("summary", "")
                if summary:
                    output.append(f"- {rel_path}\n{summary}")
                else:
                    output.append(f"- {rel_path} (non-code / empty)")
            return "\n".join(output)
            
        scored_files = []
        for rel_path, info in cache_files.items():
            score = 0
            symbols = [s.lower() for s in info.get("symbols", [])]
            path_lower = rel_path.lower()
            
            for kw in keywords:
                if kw in path_lower:
                    score += 10
                for sym in symbols:
                    if kw in sym:
                        score += 3
            scored_files.append((rel_path, score, info))
            
        scored_files.sort(key=lambda item: item[1], reverse=True)
        
        output = []
        relevant_count = 0
        for rel_path, score, info in scored_files:
            summary = info.get("summary", "")
            if score > 0 and relevant_count < max_files:
                if summary:
                    output.append(f"- {rel_path} [relevance: {score}]\n{summary}")
                else:
                    output.append(f"- {rel_path} [relevance: {score}] (empty)")
                relevant_count += 1
            else:
                output.append(f"- {rel_path}")
                
        return "\n".join(output)

    def _walk_files(self, root: Path) -> Iterator[Path]:
        for path in root.iterdir():
            if path.name in _IGNORED_PATTERNS:
                continue
            if path.is_dir():
                yield from self._walk_files(path)
            elif path.is_file():
                if path.suffix not in (".py", ".go", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".md", ".json", ".yaml", ".yml"):
                    continue
                yield path

    def _parse_file(self, filepath: Path) -> tuple[str, list[str]]:
        suffix = filepath.suffix
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                return "", []
            
            if suffix == ".py":
                return self._parse_python(content)
            elif suffix == ".go":
                return self._parse_go(content)
            elif suffix in (".js", ".ts", ".jsx", ".tsx"):
                return self._parse_js_ts(content)
        except Exception:
            pass
        return "", []

    def _parse_python(self, content: str) -> tuple[str, list[str]]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return "  [Syntax Error]", []
        
        lines: list[str] = []
        symbols: list[str] = []
        
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
                symbols.append(node.name)
            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
                base_str = f"({bases})" if bases else ""
                lines.append(f"  class {node.name}{base_str}:")
                symbols.append(node.name)
                for subnode in node.body:
                    if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        prefix = "async " if isinstance(subnode, ast.AsyncFunctionDef) else ""
                        args = format_args(subnode.args)
                        lines.append(f"    def {prefix}{subnode.name}({args})")
                        symbols.append(subnode.name)
        return "\n".join(lines), symbols

    def _parse_go(self, content: str) -> tuple[str, list[str]]:
        lines: list[str] = []
        symbols: list[str] = []
        pkg_match = re.search(r"^\s*package\s+([a-zA-Z0-9_]+)", content, re.MULTILINE)
        if pkg_match:
            lines.append(f"  package {pkg_match.group(1)}")
            symbols.append(pkg_match.group(1))
            
        func_pattern = re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\([^)]*\)[^{]*", re.MULTILINE)
        for match in func_pattern.finditer(content):
            sig = match.group(0).strip().replace("\n", " ").replace("\t", " ")
            sig = re.sub(r"\s+", " ", sig)
            lines.append(f"  {sig}")
            symbols.append(match.group(1))
        return "\n".join(lines), symbols

    def _parse_js_ts(self, content: str) -> tuple[str, list[str]]:
        lines: list[str] = []
        symbols: list[str] = []
        class_pattern = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([a-zA-Z0-9_]+)", re.MULTILINE)
        func_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\([^)]*\)", re.MULTILINE)
        arrow_pattern = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", re.MULTILINE)

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            
            c_match = class_pattern.match(line)
            if c_match:
                lines.append(f"  class {c_match.group(1)}")
                symbols.append(c_match.group(1))
                continue
                
            f_match = func_pattern.match(line)
            if f_match:
                lines.append(f"  function {f_match.group(1)}()")
                symbols.append(f_match.group(1))
                continue
                
            a_match = arrow_pattern.match(line)
            if a_match:
                lines.append(f"  const {a_match.group(1)} = () =>")
                symbols.append(a_match.group(1))
                
        return "\n".join(lines), symbols
