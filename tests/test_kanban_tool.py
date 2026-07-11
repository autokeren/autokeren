from __future__ import annotations

from pathlib import Path
from autokeren.tools.kanban import KanbanTool


def test_kanban_tool_execution(tmp_path: Path) -> None:
    tool = KanbanTool(tmp_path)

    # 1. Test add
    res = tool.run(action="add", title="Tugas TUI", description="Gunakan bubbletea", priority="high")
    assert res.ok is True
    assert "Tugas #1 berhasil ditambahkan" in res.output

    # 2. Test list
    res = tool.run(action="list")
    assert res.ok is True
    assert "#1 [TODO] Tugas TUI - Gunakan bubbletea (Priority: high)" in res.output

    # 3. Test move
    res = tool.run(action="move", task_id=1, status="in_progress")
    assert res.ok is True
    assert "Tugas #1 berhasil dipindahkan ke 'in_progress'" in res.output

    res = tool.run(action="list")
    assert "#1 [IN_PROGRESS] Tugas TUI" in res.output

    # 4. Test update
    res = tool.run(action="update", task_id=1, title="Tugas TUI Baru", priority="low")
    assert res.ok is True
    assert "Tugas #1 berhasil diperbarui" in res.output

    res = tool.run(action="list")
    assert "#1 [IN_PROGRESS] Tugas TUI Baru" in res.output
    assert "Priority: low" in res.output

    # 5. Test delete
    res = tool.run(action="delete", task_id=1)
    assert res.ok is True
    assert "Tugas #1 berhasil dihapus" in res.output

    res = tool.run(action="list")
    assert "Papan Kanban kosong" in res.output

    # 6. Test missing title for add
    res = tool.run(action="add")
    assert res.ok is False
    assert "title" in res.error

    # 7. Test missing task_id
    res = tool.run(action="update", title="Test")
    assert res.ok is False
    assert "task_id" in res.error
