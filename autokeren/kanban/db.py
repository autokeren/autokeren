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
            conn.commit()

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
