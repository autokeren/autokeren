from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class KanbanDB:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.db_path = self.project_root / ".ak-kanban.db"
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kanban_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT CHECK(status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo',
                    priority TEXT CHECK(priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            conn.commit()

        if not self.get_all_metadata():
            self._auto_seed_metadata()

    def set_metadata(self, key: str, value: str) -> None:
        query = """
            INSERT INTO project_metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """
        with self._get_connection() as conn:
            conn.execute(query, (key, value))
            conn.commit()

    def get_metadata(self, key: str, default: str = "") -> str:
        query = "SELECT value FROM project_metadata WHERE key = ?"
        with self._get_connection() as conn:
            row = conn.execute(query, (key,)).fetchone()
            return row["value"] if row else default

    def get_all_metadata(self) -> dict[str, str]:
        query = "SELECT key, value FROM project_metadata"
        with self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return {r["key"]: r["value"] for r in rows}

    def _auto_seed_metadata(self) -> None:
        path = self.project_root.resolve()
        name = path.name or "default"
        
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

        self.set_metadata("project_name", name)
        self.set_metadata("project_path", str(path))
        self.set_metadata("tech_stack", tech_stack)
        self.set_metadata("frontend_link", "http://localhost:3000")
        self.set_metadata("backend_link", "http://localhost:8787")
        self.set_metadata("runbook_install", "npm install")
        self.set_metadata("runbook_run", "npm run dev")
        self.set_metadata("runbook_test", "npm test")

    def add_task(
        self,
        title: str,
        description: str | None = None,
        status: str = "todo",
        priority: str = "medium"
    ) -> int:
        query = """
            INSERT INTO kanban_tasks (title, description, status, priority, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query, (title, description, status, priority))
            conn.commit()
            if cursor.lastrowid is None:
                raise sqlite3.DatabaseError("Gagal menyisipkan tugas baru.")
            return cursor.lastrowid

    def update_task(
        self,
        task_id: int,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None
    ) -> bool:
        fields: list[str] = []
        params: list[Any] = []

        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if description is not None:
            fields.append("description = ?")
            params.append(description)
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if priority is not None:
            fields.append("priority = ?")
            params.append(priority)

        if not fields:
            return False

        fields.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE kanban_tasks SET {', '.join(fields)} WHERE id = ?"
        params.append(task_id)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def move_task(self, task_id: int, status: str) -> bool:
        return self.update_task(task_id, status=status)

    def delete_task(self, task_id: int) -> bool:
        query = "DELETE FROM kanban_tasks WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(query, (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_tasks(self) -> list[dict[str, Any]]:
        query = "SELECT id, title, description, status, priority, created_at, updated_at FROM kanban_tasks ORDER BY id ASC"
        with self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def clear_tasks(self) -> None:
        query = "DELETE FROM kanban_tasks"
        with self._get_connection() as conn:
            conn.execute(query)
            conn.commit()
