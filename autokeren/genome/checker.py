"""Guardian checker — check for duplicate systems before file write."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from autokeren.genome.models import ProjectGenome


@dataclass
class GuardResult:
    blocked: bool = False
    reason: str = ""
    suggestion: str = ""
    warnings: list[str] = field(default_factory=list)


class GuardianChecker:
    """Check if writing a file would create duplicate system."""

    def __init__(self, genome: ProjectGenome, block_duplicates: bool = True) -> None:
        self.genome = genome
        self.block_duplicates = block_duplicates

    def check_before_write(self, file_path: str, content: str) -> GuardResult:
        result = GuardResult()
        if not self.genome.modules:
            return result

        new_funcs = self._extract_function_names(content)
        existing_module = self.genome.find_module_by_path(file_path)

        if existing_module is None and self._looks_like_new_module(file_path):
            module_name = self._infer_module_name(file_path)
            keywords = new_funcs[:5]
            similar = self.genome.find_similar_modules(module_name, keywords)
            if similar:
                result.blocked = self.block_duplicates
                names = ", ".join(m.name for m in similar)
                result.reason = (
                    f"Module '{module_name}' (dari {file_path}) tampak duplikat "
                    f"dengan module yang sudah ada: {names}"
                )
                result.suggestion = (
                    f"Gunakan module yang sudah ada: {names}. "
                    f"Jika perlu extend, tambahkan method/file di dalam module tersebut."
                )
                return result

        duplicates = self._check_function_duplicates(new_funcs, file_path)
        if duplicates:
            dup_names = [d[0] for d in duplicates]
            existing_locs = [d[1] for d in duplicates]
            result.blocked = self.block_duplicates
            result.reason = (
                f"Function(s) {dup_names} sudah ada di: {existing_locs}. "
                f"Import dari yang sudah ada daripada re-implement."
            )
            result.suggestion = (
                f"Daripada membuat ulang, import dari module yang sudah ada. "
                f"Contoh: from {existing_locs[0]} import {dup_names[0]}"
            )
            return result

        return result

    def _extract_function_names(self, content: str) -> list[str]:
        names: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            m = re.match(r"^def\s+(\w+)", stripped)
            if m:
                names.append(m.group(1))
                continue
            m = re.match(r"^class\s+(\w+)", stripped)
            if m:
                names.append(m.group(1))
                continue
            m = re.match(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", stripped)
            if m:
                names.append(m.group(1))
                continue
            m = re.match(r"^export\s+(?:const|let|var)\s+(\w+)", stripped)
            if m:
                names.append(m.group(1))
        return names

    def _looks_like_new_module(self, file_path: str) -> bool:
        parts = file_path.replace("\\", "/").split("/")
        if len(parts) <= 1:
            return False
        dir_part = parts[-2] if len(parts) >= 2 else ""
        return dir_part not in ("", ".", "..") and not file_path.startswith(("test", "spec", "tests"))

    def _infer_module_name(self, file_path: str) -> str:
        parts = file_path.replace("\\", "/").split("/")
        if len(parts) >= 2:
            return parts[-2]
        return parts[0].rsplit(".", 1)[0] if "." in parts[0] else parts[0]

    def _check_function_duplicates(self, new_funcs: list[str], file_path: str) -> list[tuple[str, str]]:
        """Check if any new function name already exists di module lain."""
        duplicates: list[tuple[str, str]] = []
        for name in new_funcs:
            entries = self.genome.function_index.get(name, [])
            for entry in entries:
                if entry.file != file_path:
                    duplicates.append((name, f"{entry.module}:{entry.file}"))
                    break
        return duplicates
