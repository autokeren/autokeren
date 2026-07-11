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
        "Spawn satu sub-agent yang akan mengerjakan task spesifik secara independen. "
        "Dapat dijalankan sinkron (in-process) atau asinkron di background (tmux session baru)."
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
            "role": {
                "type": "string",
                "description": "Peran spesifik/persona dari sub-agent (misal: 'Expert Python Tester', 'Security Auditor').",
                "default": "",
            },
            "model_id": {
                "type": "string",
                "description": "Custom Cloudflare/AI Studio model ID untuk override primary model sub-agent ini (opsional).",
                "default": "",
            },
            "background": {
                "type": "boolean",
                "description": "Jika true, sub-agent akan didelegasikan di background tmux session baru secara paralel (tidak memblokir agent saat ini). Jika false, berjalan sinkron.",
                "default": False,
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
        role = kwargs.get("role", "")
        bg = kwargs.get("background", False)
        bg_info = " (BACKGROUND)" if bg else ""
        role_info = f" ({role})" if role else ""
        return f"Spawn sub-agent '{name}'{role_info}{bg_info} untuk: {task}..."

    def run(
        self,
        task: str,
        agent_name: str = "sub-agent",
        context: str = "",
        role: str = "",
        model_id: str = "",
        background: bool = False,
    ) -> ToolResult:
        from autokeren.cli import build_registry
        from autokeren.agent import Agent
        from pathlib import Path

        full_task = task
        if context:
            full_task = f"Konteks:\n{context}\n\nTask:\n{task}"

        if background:
            from autokeren.ghost.manager import GhostManager
            try:
                mgr = GhostManager(self._project_root)
                info = mgr.spawn(full_task, role=role, model_id=model_id)
                return ToolResult(
                    output=(
                        f"[Sub-agent '{agent_name}' berhasil didelegasikan di background!]\n"
                        f"ID: #{info.id}\n"
                        f"Sesi tmux: ak-ghost-{info.id}\n"
                        f"Log file: {info.log_file}\n"
                        f"Gunakan `check_agent` tool dengan ID #{info.id} untuk memantau status tugas ini."
                    )
                )
            except Exception as e:
                return ToolResult(
                    output=f"[Gagal mendelegasikan sub-agent ke background: {e}]",
                    error=str(e),
                )

        try:
            child_reg = build_registry(self._cfg, Path(self._project_root), self._memory)  # type: ignore[arg-type]
            child_agent = Agent(
                self._cfg,  # type: ignore[arg-type]
                child_reg,
                self._project_root,
                memory=self._memory,  # type: ignore[arg-type]
                role=role,
                model_id=model_id if model_id else None,
            )
            result = child_agent.run(full_task)
            output = result if isinstance(result, str) else str(result or "")
            return ToolResult(
                output=f"[Sub-agent '{agent_name}' selesai]\n\n{output}",
            )
        except Exception as exc:
            return ToolResult(
                output=f"[Gagal menjalankan sub-agent: {exc}]",
                error=str(exc),
            )
