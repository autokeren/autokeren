from __future__ import annotations

from pathlib import Path

from autokeren.kanban.db import KanbanDB
from autokeren.tools.base import Tool, ToolResult


class KanbanTool(Tool):
    name = "kanban"
    description = (
        "Kelola papan Kanban SQLite untuk melacak tugas proyek. "
        "Aksi yang tersedia: add (tambah tugas), move (pindahkan status), update (ubah detail), "
        "delete (hapus tugas), list (lihat semua), clear (hapus semua tugas)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "move", "update", "delete", "list", "clear"],
                "description": "Aksi yang ingin dilakukan pada papan Kanban.",
            },
            "task_id": {"type": "integer", "description": "ID tugas (wajib untuk move, update, delete)."},
            "title": {"type": "string", "description": "Judul tugas baru atau perubahan judul."},
            "description": {"type": "string", "description": "Deskripsi tugas baru atau perubahan deskripsi."},
            "status": {
                "type": "string",
                "enum": ["todo", "in_progress", "done"],
                "description": "Status tugas (todo, in_progress, done).",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Prioritas tugas (low, medium, high).",
            },
        },
        "required": ["action"],
    }

    def __init__(self, project_root: Path) -> None:
        self.db = KanbanDB(project_root)

    def run(
        self,
        action: str,
        task_id: int = 0,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        **_: object
    ) -> ToolResult:
        try:
            if action == "add":
                if not title:
                    return ToolResult(error="Parameter 'title' wajib diisi untuk aksi 'add'.", ok=False)
                new_id = self.db.add_task(
                    title=title,
                    description=description,
                    status=status or "todo",
                    priority=priority or "medium"
                )
                return ToolResult(output=f"✓ Tugas #{new_id} berhasil ditambahkan ke papan Kanban.")

            if action == "move":
                if task_id <= 0:
                    return ToolResult(error="Parameter 'task_id' wajib diisi dengan nilai > 0 untuk aksi 'move'.", ok=False)
                if not status:
                    return ToolResult(error="Parameter 'status' wajib diisi untuk aksi 'move'.", ok=False)
                success = self.db.move_task(task_id, status)
                if success:
                    return ToolResult(output=f"✓ Tugas #{task_id} berhasil dipindahkan ke '{status}'.")
                return ToolResult(error=f"Tugas dengan ID {task_id} tidak ditemukan.", ok=False)

            if action == "update":
                if task_id <= 0:
                    return ToolResult(error="Parameter 'task_id' wajib diisi dengan nilai > 0 untuk aksi 'update'.", ok=False)
                success = self.db.update_task(
                    task_id=task_id,
                    title=title,
                    description=description,
                    status=status,
                    priority=priority
                )
                if success:
                    return ToolResult(output=f"✓ Tugas #{task_id} berhasil diperbarui.")
                return ToolResult(error=f"Tugas dengan ID {task_id} tidak ditemukan atau tidak ada perubahan field.", ok=False)

            if action == "delete":
                if task_id <= 0:
                    return ToolResult(error="Parameter 'task_id' wajib diisi dengan nilai > 0 untuk aksi 'delete'.", ok=False)
                success = self.db.delete_task(task_id)
                if success:
                    return ToolResult(output=f"✓ Tugas #{task_id} berhasil dihapus dari papan Kanban.")
                return ToolResult(error=f"Tugas dengan ID {task_id} tidak ditemukan.", ok=False)

            if action == "list":
                tasks = self.db.list_tasks()
                if not tasks:
                    return ToolResult(output="Papan Kanban kosong.")
                lines = []
                for t in tasks:
                    desc_part = f" - {t['description']}" if t['description'] else ""
                    lines.append(f"#{t['id']} [{t['status'].upper()}] {t['title']}{desc_part} (Priority: {t['priority']})")
                return ToolResult(output="\n".join(lines))

            if action == "clear":
                self.db.clear_tasks()
                return ToolResult(output="✓ Seluruh tugas di papan Kanban berhasil dibersihkan.")

            return ToolResult(error=f"Aksi tidak dikenal: {action}", ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)
