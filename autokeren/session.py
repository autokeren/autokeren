"""Session manager — save/resume/list sessions per project using SQLite."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from autokeren.memory import _config_base, _project_slug
from autokeren.utils import now_iso


class SessionManager:
    """Kelola save/resume session per project menggunakan SQLite.

    Database disimpan di ~/.config/autokeren/projects/<slug>/sessions/sessions.db
    Tabel sessions berisi: id, name, project, timestamp, messages (JSON), usage (JSON).
    """

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.sessions_dir = _config_base() / "projects" / _project_slug(project_root) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.sessions_dir / "sessions.db"
        self._init_db()

    def _init_db(self) -> None:
        """Inisialisasi tabel SQLite dan migrasikan file JSON lama jika ada."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    project TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    usage TEXT NOT NULL
                )
            """)
            conn.commit()

            # Migrasi data JSON lama ke SQLite secara otomatis
            for p in self.sessions_dir.glob("*.json"):
                if p.name == "sessions.json":
                    continue
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    sid = data.get("id")
                    name = data.get("name")
                    project = data.get("project", str(self.project_root))
                    timestamp = data.get("timestamp", now_iso())
                    messages = json.dumps(data.get("messages", []))
                    usage = json.dumps(data.get("usage", {}))

                    if sid and name:
                        conn.execute(
                            "INSERT OR IGNORE INTO sessions (id, name, project, timestamp, messages, usage) VALUES (?, ?, ?, ?, ?, ?)",
                            (sid, name, project, timestamp, messages, usage)
                        )
                    # Hapus file JSON setelah sukses dipindahkan ke database
                    p.unlink()
                except Exception:
                    continue
            conn.commit()

    def save(self, name: str, messages: list[dict[str, Any]], usage: dict[str, Any], session_id: str | None = None) -> str:
        """Save session. Return session_id.

        Kalau session_id diberikan, update session yang sudah ada.
        Kalau None, buat session baru.
        """
        timestamp = now_iso()
        if session_id:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE sessions SET name = ?, timestamp = ?, messages = ?, usage = ? WHERE id = ?",
                    (name, timestamp, json.dumps(messages), json.dumps(usage), session_id),
                )
                if cursor.rowcount > 0:
                    conn.commit()
                    return session_id
            # Fall through: session_id tidak ditemukan, buat baru

        session_id = now_iso().replace(":", "").replace("-", "")[:14]
        timestamp = now_iso()

        # Hindari tabrakan ID untuk pemanggilan sangat cepat
        base_id = session_id
        counter = 1
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            while True:
                cursor.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,))
                if not cursor.fetchone():
                    break
                session_id = f"{base_id}-{counter}"
                counter += 1

            conn.execute(
                "INSERT OR REPLACE INTO sessions (id, name, project, timestamp, messages, usage) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, name, str(self.project_root), timestamp, json.dumps(messages), json.dumps(usage))
            )
            conn.commit()
        return session_id

    def load(self, identifier: str) -> dict[str, Any] | None:
        """Load session by id, name, atau partial name. Return data atau None."""
        if not self.db_path.exists():
            return None
            
        identifier_lower = identifier.lower()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Cari exact match
            cursor.execute(
                "SELECT id, name, project, timestamp, messages, usage FROM sessions WHERE lower(id) = ? OR lower(name) = ?",
                (identifier_lower, identifier_lower)
            )
            row = cursor.fetchone()
            if not row:
                # Cari partial match, ambil yang terbaru
                cursor.execute(
                    "SELECT id, name, project, timestamp, messages, usage FROM sessions WHERE lower(id) LIKE ? OR lower(name) LIKE ? ORDER BY timestamp DESC LIMIT 1",
                    (f"%{identifier_lower}%", f"%{identifier_lower}%")
                )
                row = cursor.fetchone()
                
            if row:
                sid, name, project, timestamp, messages_str, usage_str = row
                try:
                    messages = json.loads(messages_str)
                    usage = json.loads(usage_str)
                    return {
                        "id": sid,
                        "name": name,
                        "project": project,
                        "timestamp": timestamp,
                        "messages": messages,
                        "usage": usage,
                    }
                except Exception:
                    pass
        return None

    def list(self) -> list[dict[str, Any]]:
        """List semua saved sessions, newest first."""
        if not self.db_path.exists():
            return []
            
        sessions: list[dict[str, Any]] = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, timestamp, messages FROM sessions ORDER BY timestamp DESC")
            for row in cursor.fetchall():
                sid, name, timestamp, messages_str = row
                try:
                    msg_count = len(json.loads(messages_str))
                except Exception:
                    msg_count = 0
                sessions.append({
                    "id": sid,
                    "name": name,
                    "timestamp": timestamp,
                    "messages": msg_count,
                    "file": "sqlite",
                })
        return sessions

    def delete(self, identifier: str) -> bool:
        """Hapus session by identifier."""
        if not self.db_path.exists():
            return False
            
        identifier_lower = identifier.lower()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM sessions WHERE lower(id) = ? OR lower(name) = ?",
                (identifier_lower, identifier_lower)
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "SELECT id FROM sessions WHERE lower(id) LIKE ? OR lower(name) LIKE ?",
                    (f"%{identifier_lower}%", f"%{identifier_lower}%")
                )
                row = cursor.fetchone()
                
            if row:
                sid = row[0]
                cursor.execute("DELETE FROM sessions WHERE id = ?", (sid,))
                conn.commit()
                return True
        return False
