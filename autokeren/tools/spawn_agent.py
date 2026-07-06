"""autokeren.tools.spawn_agent — Tool untuk spawn sub-agent secara otomatis."""
from __future__ import annotations

from autokeren.tools.base import Tool, ToolResult


class SpawnAgentTool(Tool):
    """Tool yang memungkinkan agent utama menjalankan sub-agent secara paralel atau serial.

    AI dapat memanggil tool ini ketika sebuah task lebih baik dikerjakan
    oleh agent terpisah yang fokus pada satu pekerjaan saja, misalnya:
    - Menjalankan riset dan penulisan kode secara bersamaan
    - Memisahkan task backend dari frontend
    - Menjalankan verifikasi independen pada output

    Output sub-agent dikembalikan ke agent utama sebagai string hasil.
    """

    name = "spawn_agent"
    description = (
        "Spawn satu sub-agent yang akan mengerjakan task spesifik secara independen dan mengembalikan hasilnya. "
        "Gunakan tool ini saat satu task bisa diparalelkan atau membutuhkan fokus terpisah dari conversation utama. "
        "Sub-agent memiliki akses ke semua tool yang sama. Hasil dikembalikan sebagai teks setelah selesai."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Deskripsi task yang harus dikerjakan oleh sub-agent. Semakin jelas semakin baik.",
            },
            "agent_name": {
                "type": "string",
                "description": "Nama/label untuk sub-agent ini, digunakan untuk tracking (misal: 'backend', 'researcher', 'tester').",
                "default": "sub-agent",
            },
            "context": {
                "type": "string",
                "description": "Konteks tambahan yang perlu diketahui sub-agent (opsional, misal: output tool sebelumnya).",
                "default": "",
            },
        },
        "required": ["task"],
    }
    requires_permission = True

    def __init__(self, cfg: object, project_root: str, memory: object) -> None:
        self._cfg = cfg
        self._project_root = project_root
        self._memory = memory

    def permission_desc(self, **kwargs: object) -> str:
        name = kwargs.get("agent_name", "sub-agent")
        task = str(kwargs.get("task", ""))[:80]
        return f"Spawn sub-agent '{name}' untuk: {task}..."

    def run(self, task: str, agent_name: str = "sub-agent", context: str = "") -> ToolResult:
        from autokeren.cli import build_registry
        from autokeren.agent import Agent
        from pathlib import Path

        full_task = task
        if context:
            full_task = f"Konteks:\n{context}\n\nTask:\n{task}"

        try:
            child_reg = build_registry(self._cfg, Path(self._project_root), self._memory)  # type: ignore[arg-type]
            child_agent = Agent(self._cfg, child_reg, self._project_root, memory=self._memory)  # type: ignore[arg-type]
            result = child_agent.run(full_task)
            output = result if isinstance(result, str) else str(result or "")
            return ToolResult(
                output=f"[Sub-agent '{agent_name}' selesai]\n\n{output}",
            )
        except Exception as exc:
            return ToolResult(
                output=f"[Sub-agent '{agent_name}' gagal: {exc}]",
                error=str(exc),
            )
