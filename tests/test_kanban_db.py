from __future__ import annotations

from pathlib import Path
from autokeren.kanban.db import KanbanDB


def test_kanban_db_crud(tmp_path: Path) -> None:
    db = KanbanDB(tmp_path)
    assert db.db_path.exists()

    # 1. Add tasks
    task_id1 = db.add_task("Membangun TUI", "Menggunakan bubbletea", "todo", "high")
    task_id2 = db.add_task("Menulis Unit Test", "Menggunakan pytest", "todo", "medium")

    assert task_id1 == 1
    assert task_id2 == 2

    # 2. List tasks
    tasks = db.list_tasks()
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Membangun TUI"
    assert tasks[0]["priority"] == "high"
    assert tasks[0]["status"] == "todo"

    # 3. Move task
    success = db.move_task(task_id1, "in_progress")
    assert success is True

    tasks = db.list_tasks()
    assert tasks[0]["status"] == "in_progress"

    # 4. Update task
    success = db.update_task(task_id2, title="Tulis Test Suite", priority="low")
    assert success is True

    tasks = db.list_tasks()
    assert tasks[1]["title"] == "Tulis Test Suite"
    assert tasks[1]["priority"] == "low"

    # 5. Delete task
    success = db.delete_task(task_id1)
    assert success is True

    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["id"] == task_id2

    # 6. Clear tasks
    db.clear_tasks()
    assert len(db.list_tasks()) == 0
