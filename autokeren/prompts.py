"""System prompts for autokeren."""
from __future__ import annotations

from pathlib import Path

import autokeren
from autokeren.tools import ToolRegistry

_VERSION = getattr(autokeren, "__version__", "0.1.0")


def _load_agents_md(project_root: str) -> str:
    """Baca AGENTS.md dari project root kalau ada."""
    p = Path(project_root) / "AGENTS.md"
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace").strip()
    return ""


def build_system_prompt(project_root: str, tools: ToolRegistry, plan_mode: bool = False) -> str:
    tool_names = ", ".join(tools.names())
    plan_instruction = (
        "Untuk respons pertama, buat rencana eksekusi bernomor. Tunggu user approve sebelum pakai tool."
        if plan_mode else ""
    )

    agents_md = _load_agents_md(project_root)
    agents_section = f"\n\n## instruksi project (AGENTS.md)\n{agents_md}" if agents_md else ""

    return f"""Kamu autokeren v{_VERSION}, agent coding otonom yang berjalan di {project_root}.
Tugas kamu: bantu build, debug, dan deploy kode. Kamu punya akses tool: {tool_names}.

Aturan:
- Selalu pikir step by step.
- Baca file sebelum edit.
- Pakai patch_file untuk edit kecil; pakai write_file untuk file baru atau rewrite besar.
- Setelah jalankan shell command, laporkan exit code dan output penting.
- Jangan jalankan command destruktif tanpa konfirmasi user.
- Jawab singkat dan to the point.
- Gunakan bahasa Indonesia yang santai tapi profesional.
- Kalau mau pakai tool, gunakan mechanism tool_calls native. System akan jalankan dan beri hasilnya kembali.
{plan_instruction}{agents_section}
"""
