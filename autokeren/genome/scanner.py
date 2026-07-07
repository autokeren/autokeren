"""Genome scanner — scan project structure, imports, functions."""
from __future__ import annotations

import re
import time
from pathlib import Path

from autokeren.genome.models import Dependency, FunctionEntry, Module, ProjectGenome

_IGNORED_DIRS = frozenset({
    ".git", ".svn", ".hg", ".venv", "venv", "env", "__pycache__",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", "node_modules",
    ".next", ".nuxt", ".turbo", "build", "dist", ".eggs", "*.egg-info",
    ".tox", "htmlcov", ".coverage", ".idea", ".vscode", ".ak-checkpoints",
})

_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java",
}

_INIT_FILES = {"__init__.py", "index.ts", "index.js", "index.tsx", "index.jsx", "mod.rs"}


class GenomeScanner:
    """Scan project dan build ProjectGenome."""

    def __init__(self, project_root: Path) -> None:
        self.root = project_root

    def scan(self) -> ProjectGenome:
        genome = ProjectGenome(
            root=str(self.root),
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._detect_modules(genome)
        self._analyze_functions(genome)
        self._analyze_imports(genome)
        return genome

    def _detect_modules(self, genome: ProjectGenome) -> None:
        """Detect modules: directories with init files atau top-level code dirs."""
        for p in sorted(self._walk_skipping_ignored(self.root)):
            if not p.is_dir():
                continue
            rel = p.relative_to(self.root)
            has_init = any((p / init).exists() for init in _INIT_FILES)
            has_code = any(p.suffix in _CODE_EXTENSIONS for p in p.iterdir() if p.is_file())
            if has_init or (has_code and len(rel.parts) <= 3):
                mod_name = str(rel).replace("/", ".").replace("\\", ".")
                if not mod_name or mod_name == ".":
                    continue
                language = self._detect_language(p)
                key_files = [
                    str(f.relative_to(self.root))
                    for f in sorted(p.iterdir())
                    if f.is_file() and f.suffix in _CODE_EXTENSIONS
                ][:10]
                genome.modules.append(Module(
                    name=mod_name,
                    path=str(rel),
                    language=language,
                    key_files=key_files,
                ))

    def _walk_skipping_ignored(self, root: Path, max_depth: int = 4) -> list[Path]:
        """Walk directory tree, skipping ignored dirs entirely (faster on Windows)."""
        results: list[Path] = []
        stack = [(root, 0)]
        while stack:
            current, depth = stack.pop()
            if depth > max_depth:
                continue
            try:
                for entry in current.iterdir():
                    if entry.is_dir():
                        if entry.name in _IGNORED_DIRS:
                            continue
                        results.append(entry)
                        stack.append((entry, depth + 1))
                    else:
                        results.append(entry)
            except (PermissionError, OSError):
                continue
        return results

    def _detect_language(self, dir_path: Path) -> str:
        for f in dir_path.iterdir():
            if f.suffix == ".py":
                return "python"
            if f.suffix in (".ts", ".tsx"):
                return "typescript"
            if f.suffix in (".js", ".jsx"):
                return "javascript"
            if f.suffix == ".rs":
                return "rust"
            if f.suffix == ".go":
                return "go"
        return "unknown"

    def _analyze_functions(self, genome: ProjectGenome) -> None:
        """Index top-level function/class definitions."""
        for mod in genome.modules:
            for file_rel in mod.key_files:
                file_path = self.root / file_rel
                if not file_path.exists():
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                funcs = self._extract_functions(content, mod.name, file_rel)
                mod.functions.extend(funcs)
                for f in funcs:
                    genome.function_index.setdefault(f.name, []).append(f)

    def _extract_functions(self, content: str, module: str, file: str) -> list[FunctionEntry]:
        entries: list[FunctionEntry] = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            m = re.match(r"^def\s+(\w+)\s*\(([^)]*)\)", stripped)
            if m:
                entries.append(FunctionEntry(
                    name=m.group(1), module=module, file=file, line=i,
                    signature=f"def {m.group(1)}({m.group(2)})",
                ))
                continue
            m = re.match(r"^class\s+(\w+)", stripped)
            if m:
                entries.append(FunctionEntry(
                    name=m.group(1), module=module, file=file, line=i,
                    signature=f"class {m.group(1)}",
                ))
                continue
            m = re.match(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", stripped)
            if m:
                entries.append(FunctionEntry(
                    name=m.group(1), module=module, file=file, line=i,
                    signature=stripped[:80],
                ))
                continue
            m = re.match(r"^export\s+(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(", stripped)
            if m:
                entries.append(FunctionEntry(
                    name=m.group(1), module=module, file=file, line=i,
                    signature=stripped[:80],
                ))
        return entries

    def _analyze_imports(self, genome: ProjectGenome) -> None:
        """Analyze import relationships antar modules."""
        for mod in genome.modules:
            for file_rel in mod.key_files:
                file_path = self.root / file_rel
                if not file_path.exists():
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                targets = self._extract_imports(content, mod.language if mod.language else "")
                for target in targets:
                    target_mod = self._resolve_import_target(target, genome.modules)
                    if target_mod and target_mod.name != mod.name:
                        dep = Dependency(from_module=mod.name, to_module=target_mod.name)
                        if dep not in genome.dependencies:
                            genome.dependencies.append(dep)

    def _extract_imports(self, content: str, language: str) -> list[str]:
        imports: list[str] = []
        if language == "python":
            for m in re.finditer(r"^\s*from\s+([\w.]+)\s+import", content, re.M):
                imports.append(m.group(1))
            for m in re.finditer(r"^\s*import\s+([\w.]+)", content, re.M):
                imports.append(m.group(1))
        elif language in ("javascript", "typescript"):
            for m in re.finditer(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", content):
                imports.append(m.group(1))
            for m in re.finditer(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
                imports.append(m.group(1))
        return imports

    def _resolve_import_target(self, import_path: str, modules: list[Module]) -> Module | None:
        """Resolve import path ke module."""
        parts = import_path.replace("/", ".").replace("\\", ".").lstrip(".")
        for mod in modules:
            if mod.name == parts or parts.startswith(mod.name + "."):
                return mod
        return None
