"""Genome tool — view/rescan project genome for Architecture Guardian."""
from __future__ import annotations

from typing import Any

from autokeren.genome.scanner import GenomeScanner
from autokeren.genome.models import ProjectGenome
from autokeren.tools.base import Tool, ToolResult


class GenomeTool(Tool):
    name = "genome"
    description = (
        "Lihat atau rescan project genome (peta arsitektur). "
        "Menampilkan modules, dependencies, dan duplicate functions. "
        "Gunakan untuk memahami struktur project sebelum menulis code."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "view (lihat genome), rescan (scan ulang), check (cek duplicates)",
                "default": "view",
            },
        },
    }

    def __init__(self, scanner: GenomeScanner, genome: ProjectGenome) -> None:
        self._scanner = scanner
        self._genome = genome

    def run(self, action: str = "view", **_: Any) -> ToolResult:
        if action == "rescan":
            self._genome = self._scanner.scan()
            return ToolResult(output=self._format_summary())
        if action == "check":
            dups = self._genome.find_duplicate_functions()
            if not dups:
                return ToolResult(output="Tidak ada duplicate functions ditemukan.")
            lines = ["Duplicate functions:\n"]
            for name, entries in dups.items():
                locs = ", ".join(f"{e.module}:{e.file}:{e.line}" for e in entries)
                lines.append(f"  • {name} — {locs}")
            return ToolResult(output="\n".join(lines))
        return ToolResult(output=self._format_summary())

    def _format_summary(self) -> str:
        g = self._genome
        lines = [f"Project Genome ({len(g.modules)} modules, {len(g.dependencies)} deps)\n"]
        for m in g.modules:
            lines.append(f"  [{m.language}] {m.name} ({m.path}) — {len(m.key_files)} files, {len(m.functions)} functions")
        dups = g.find_duplicate_functions()
        if dups:
            lines.append(f"\n⚠ {len(dups)} duplicate functions:")
            for name, entries in dups.items():
                locs = ", ".join(f"{e.module}" for e in entries)
                lines.append(f"  • {name} — {locs}")
        return "\n".join(lines)
