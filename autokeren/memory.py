"""Memory manager — per-project persistent memory across sessions."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from autokeren.utils import now_iso, sanitize_filename

_MAX_MEMORY_LINES = 200


def _project_slug(project_root: str) -> str:
    name = Path(project_root).name or "default"
    h = hashlib.md5(str(Path(project_root).resolve()).encode()).hexdigest()[:8]
    return f"{sanitize_filename(name)}-{h}"


def _config_base() -> Path:
    return Path(os.environ.get("AUTOKEREN_CONFIG_DIR", Path.home() / ".config" / "autokeren"))


class MemoryManager:
    """Kelola memory.md per project. Disimpan di ~/.config/autokeren/projects/<slug>/memory.md.

    Memory diload ke system prompt setiap startup (200 baris pertama).
    Agent bisa append via remember tool. User bisa edit via /memory.
    """

    def __init__(self, project_root: str, max_lines: int = _MAX_MEMORY_LINES):
        self.project_root = project_root
        self.max_lines = max_lines
        self.project_dir = _config_base() / "projects" / _project_slug(project_root)
        self.memory_file = self.project_dir / "memory.md"

    def load(self) -> str:
        """Load memory content (max max_lines baris)."""
        if not self.memory_file.exists() or self.memory_file.stat().st_size == 0:
            self._initialize_default_memory()
        lines = self.memory_file.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[: self.max_lines])

    def _initialize_default_memory(self) -> None:
        """Inisialisasi file memory.md default dengan metadata proyek."""
        path = Path(self.project_root).resolve()
        name = path.name or "default"
        
        # Tebak tech stack
        stacks = []
        if (path / "package.json").exists():
            stacks.append("Node.js")
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists() or (path / "setup.py").exists():
            stacks.append("Python")
        if (path / "go.mod").exists():
            stacks.append("Go")
        if (path / "Cargo.toml").exists():
            stacks.append("Rust")
        if (path / "wrangler.toml").exists() or (path / "wrangler.json").exists():
            stacks.append("Cloudflare Workers")
        tech_stack = ", ".join(stacks) if stacks else "Unknown"

        template = (
            f"# Project Memory: {name}\n\n"
            f"## Metadata Proyek\n"
            f"- **Nama Project**: {name}\n"
            f"- **Direktori**: {path}\n"
            f"- **Teknologi**: {tech_stack}\n"
            f"- **Link Frontend (FE)**: (Silakan diisi, contoh: http://localhost:3000)\n"
            f"- **Link Backend (BE)**: (Silakan diisi, contoh: http://localhost:8787)\n\n"
            f"## Panduan / Runbook\n"
            f"- **Install Dependencies**: (contoh: npm install atau pip install)\n"
            f"- **Jalankan Aplikasi**: (contoh: npm run dev)\n"
            f"- **Jalankan Pengujian**: (contoh: pytest atau npm test)\n\n"
            f"## Catatan Kunci & Context\n"
            f"- Proyek ini dikelola menggunakan autokeren CLI.\n"
        )
        self.save(template)

    def save(self, content: str) -> None:
        """Overwrite memory file."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(content, encoding="utf-8")

    def append(self, section: str, note: str) -> str:
        """Append note ke section tertentu. Buat section kalau belum ada."""
        existing = ""
        if self.memory_file.exists():
            existing = self.memory_file.read_text(encoding="utf-8", errors="replace")

        header = f"## {section}"
        if header in existing:
            existing = existing.replace(header + "\n", header + f"\n- {note}\n")
        else:
            ts = now_iso()[:10]
            if existing and not existing.endswith("\n"):
                existing += "\n"
            existing += f"\n{header}\n_Update: {ts}_\n- {note}\n"

        self.save(existing)
        return existing

    def clear(self) -> None:
        """Hapus semua memory."""
        if self.memory_file.exists():
            self.memory_file.write_text("", encoding="utf-8")

    def get_path(self) -> Path:
        return self.memory_file

    def exists(self) -> bool:
        return self.memory_file.exists()

    def line_count(self) -> int:
        if not self.memory_file.exists():
            return 0
        return len(self.memory_file.read_text(encoding="utf-8", errors="replace").splitlines())
