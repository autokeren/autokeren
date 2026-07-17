"""Codebase structure indexing tool (Repo Map) with caching, AST dependency graphing, and relevance filtering."""
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
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    content = ""
                summary, symbols = self._parse_file(filepath)
                deps = self._extract_dependencies(filepath, content)
                cache_files[rel_path] = {
                    "mtime": mtime,
                    "summary": summary,
                    "symbols": symbols,
                    "dependencies": deps,
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
        
        base_relevant_limit = max(1, max_files // 2)
        top_matches = [item for item in scored_files if item[1] > 0][:base_relevant_limit]
        
        high_relevance_set = {item[0] for item in top_matches}
        for rel_path, score, info in top_matches:
            deps = info.get("dependencies", [])
            for dep in deps:
                if dep in cache_files and len(high_relevance_set) < max_files:
                    high_relevance_set.add(dep)
                    
        for rel_path, score, info in scored_files:
            if score > 0 and rel_path not in high_relevance_set and len(high_relevance_set) < max_files:
                high_relevance_set.add(rel_path)
                
        output = []
        for rel_path, info in sorted(cache_files.items()):
            summary = info.get("summary", "")
            if rel_path in high_relevance_set:
                output.append(f"- {rel_path}\n{summary}")
            else:
                output.append(f"- {rel_path}")
                
        return "\n".join(output)

    def _extract_dependencies(self, filepath: Path, content: str) -> list[str]:
        deps = []
        suffix = filepath.suffix
        
        if suffix == ".py":
            import_pat = re.compile(r"^\s*(?:import\s+([a-zA-Z0-9_.]+)|from\s+([a-zA-Z0-9_.]+)\s+import)", re.MULTILINE)
            relative_pat = re.compile(r"^\s*from\s+(\.+)([a-zA-Z0-9_.]*)\s+import", re.MULTILINE)
            
            for match in import_pat.finditer(content):
                mod_name = match.group(1) or match.group(2)
                if not mod_name:
                    continue
                if mod_name.startswith("autokeren"):
                    parts = mod_name.split(".")
                    py_path = "/".join(parts) + ".py"
                    init_path = "/".join(parts) + "/__init__.py"
                    if (self.project_root / py_path).exists():
                        deps.append(py_path)
                    elif (self.project_root / init_path).exists():
                        deps.append(init_path)
                        
            for match in relative_pat.finditer(content):
                dots = len(match.group(1))
                sub_mod = match.group(2)
                target_dir = filepath.parent
                for _ in range(dots - 1):
                    target_dir = target_dir.parent
                
                rel_parts = sub_mod.split(".") if sub_mod else []
                if rel_parts:
                    py_filepath = target_dir / ("/".join(rel_parts) + ".py")
                    init_filepath = target_dir / ("/".join(rel_parts) + "/__init__.py")
                    if py_filepath.exists():
                        deps.append(str(py_filepath.relative_to(self.project_root)))
                    elif init_filepath.exists():
                        deps.append(str(init_filepath.relative_to(self.project_root)))
                else:
                    init_filepath = target_dir / "__init__.py"
                    if init_filepath.exists():
                        deps.append(str(init_filepath.relative_to(self.project_root)))
                        
        elif suffix == ".go":
            go_module = "github.com/autokeren/autokeren"
            import_pat = re.compile(r'"' + re.escape(go_module) + r'/([^"]+)"')
            for match in import_pat.finditer(content):
                pkg_path = match.group(1)
                pkg_dir = self.project_root / pkg_path
                if pkg_dir.exists() and pkg_dir.is_dir():
                    for f in pkg_dir.iterdir():
                        if f.is_file() and f.suffix == ".go":
                            deps.append(str(f.relative_to(self.project_root)))
                            
        elif suffix in (".js", ".ts", ".jsx", ".tsx"):
            import_pat = re.compile(r"(?:import|from)\s+['\"](\.[^'\"]+)['\"]")
            for match in import_pat.finditer(content):
                rel_path = match.group(1)
                target_path = (filepath.parent / rel_path).resolve()
                
                for ext in (".ts", ".js", ".tsx", ".jsx"):
                    f_path = target_path.with_suffix(ext)
                    if f_path.exists() and f_path.is_relative_to(self.project_root):
                        deps.append(str(f_path.relative_to(self.project_root)))
                        break
                else:
                    for ext in (".ts", ".js", ".tsx", ".jsx"):
                        f_path = target_path / f"index{ext}"
                        if f_path.exists() and f_path.is_relative_to(self.project_root):
                            deps.append(str(f_path.relative_to(self.project_root)))
                            break
                            
        return sorted(list(set(deps)))

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
