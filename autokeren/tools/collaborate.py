from __future__ import annotations

from pathlib import Path

from autokeren.tools.base import Tool, ToolResult


class CollaborateTool(Tool):
    """Tool untuk kolaborasi dua arah (tektokan) antara Coder dan Critic."""

    name = "collaborate"
    description = (
        "Mulai sesi kolaborasi dan perdebatan dua arah (Critic-Coder loop) untuk menyelesaikan tugas dengan kualitas tinggi. "
        "Dua sub-agent (Coder dan Critic) akan saling tektokan menulis dan mengulas kode sampai disetujui."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Deskripsi tugas utama yang ingin dikerjakan.",
            },
            "coder_role": {
                "type": "string",
                "description": "Peran/spesialisasi sub-agent penulis kode (misal: 'Expert Python Developer').",
                "default": "Expert Python Programmer",
            },
            "critic_role": {
                "type": "string",
                "description": "Peran/spesialisasi sub-agent pengulas/kritik (misal: 'Senior Security Auditor').",
                "default": "Senior Security & Quality Reviewer",
            },
            "max_turns": {
                "type": "integer",
                "description": "Jumlah putaran debat/tektokan maksimal (default: 3).",
                "default": 3,
            },
            "model_id": {
                "type": "string",
                "description": "Model ID kustom untuk sub-agent (opsional).",
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
        task = str(kwargs.get("task", ""))[:80]
        return f"Mulai kolaborasi Critic-Coder loop untuk tugas: {task}..."

    def run(
        self,
        task: str,
        coder_role: str = "Expert Python Programmer",
        critic_role: str = "Senior Security & Quality Reviewer",
        max_turns: int = 3,
        model_id: str = "",
        **_: object,
    ) -> ToolResult:
        from autokeren.cli import build_registry
        from autokeren.agent import Agent

        print("\n==================================================")
        print("👥 MULTI-AGENT COLLABORATION: CRITIC-CODER LOOP")
        print(f"📌 Task: {task}")
        print(f"👨‍💻 Coder Role: {coder_role}")
        print(f"🕵️‍♂️ Critic Role: {critic_role}")
        print("==================================================\n")

        try:
            child_reg = build_registry(self._cfg, Path(self._project_root), self._memory)  # type: ignore[arg-type]
            
            coder_agent = Agent(
                self._cfg,  # type: ignore[arg-type]
                child_reg,
                self._project_root,
                memory=self._memory,  # type: ignore[arg-type]
                role=coder_role,
                model_id=model_id if model_id else None,
            )

            critic_agent = Agent(
                self._cfg,  # type: ignore[arg-type]
                child_reg,
                self._project_root,
                memory=self._memory,  # type: ignore[arg-type]
                role=critic_role,
                model_id=model_id if model_id else None,
            )

            current_code = ""
            feedback = ""

            for turn in range(max_turns):
                print(f"\n--- [PUTARAN {turn + 1}/{max_turns}] ---")
                
                # --- A. Coder Turn ---
                print(f"\n[👨‍💻 {coder_role} sedang bekerja...]")
                if turn == 0:
                    prompt = f"Tugas Utama: {task}\nSilakan kerjakan tugas ini dan tulis kodenya secara lengkap."
                else:
                    prompt = (
                        f"Kritik dari Reviewer:\n{feedback}\n\n"
                        f"Perbaiki kode Anda berdasarkan kritik di atas. Tulis ulang kode yang diperbaiki secara lengkap."
                    )
                
                coder_resp = coder_agent.run(prompt)
                current_code = coder_resp.content or ""
                print(f"\n[👨‍💻 {coder_role} menghasilkan solusi:]\n{current_code}")

                # --- B. Critic Turn ---
                print(f"\n[🕵️‍♂️ {critic_role} sedang meninjau...]")
                critic_prompt = (
                    f"Tugas Utama: {task}\n\n"
                    f"Kode yang dihasilkan Coder:\n{current_code}\n\n"
                    f"Ulas kode di atas secara kritis untuk memastikan tidak ada bug, masalah keamanan, "
                    f"atau pelanggaran struktur arsitektur. Jika kode sudah sempurna tanpa cacat, cukup balas dengan 'APPROVED'. "
                    f"Jika ada kekurangan, jelaskan detail perbaikan yang diperlukan."
                )
                
                critic_resp = critic_agent.run(critic_prompt)
                feedback = critic_resp.content or ""
                print(f"\n[🕵️‍♂️ {critic_role} memberikan ulasan:]\n{feedback}")

                if "approved" in feedback.lower() or "passed" in feedback.lower():
                    print("\n✅ [KOLABORASI SELESAI] Kode disetujui oleh Critic!")
                    break

            return ToolResult(
                output=(
                    f"✓ Sesi kolaborasi multi-agent selesai setelah {turn + 1} putaran.\n\n"
                    f"Hasil Ulasan Akhir:\n{feedback}\n\n"
                    f"Hasil Kode Akhir:\n{current_code}"
                )
            )

        except Exception as exc:
            return ToolResult(
                output=f"[Gagal menjalankan kolaborasi: {exc}]",
                error=str(exc),
            )
