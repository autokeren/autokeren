"""Tests for Time-Travel /rewind checkpoint system."""
from __future__ import annotations

from pathlib import Path

from autokeren.checkpoints.manager import CheckpointManager


def test_checkpoint_save_and_count(tmp_path: Path):
    """Save checkpoint → count increases."""
    mgr = CheckpointManager(tmp_path, session_id="test")
    assert mgr.count() == 0
    mgr.save(
        tool_name="write_file",
        tool_args={"path": "test.py", "content": "print('hello')"},
        tool_result={"ok": True},
        tool_ok=True,
        before_snapshot={"test.py": None},
    )
    assert mgr.count() == 1


def test_rewind_write_file_creates(tmp_path: Path):
    """write_file creates file → rewind deletes it."""
    mgr = CheckpointManager(tmp_path, session_id="test")
    target = tmp_path / "hello.py"
    before = mgr.snapshot_files(["hello.py"])
    target.write_text("print('hello')")
    mgr.save(
        tool_name="write_file",
        tool_args={"path": "hello.py"},
        tool_result={"ok": True},
        tool_ok=True,
        before_snapshot=before,
    )
    assert target.exists()
    undone = mgr.rewind(1)
    assert len(undone) == 1
    assert not target.exists()


def test_rewind_modify_file(tmp_path: Path):
    """write_file modifies existing → rewind restores original."""
    mgr = CheckpointManager(tmp_path, session_id="test")
    target = tmp_path / "config.py"
    target.write_text("DEBUG = False")
    before = mgr.snapshot_files(["config.py"])
    target.write_text("DEBUG = True")
    mgr.save(
        tool_name="write_file",
        tool_args={"path": "config.py"},
        tool_result={"ok": True},
        tool_ok=True,
        before_snapshot=before,
    )
    assert target.read_text() == "DEBUG = True"
    mgr.rewind(1)
    assert target.read_text() == "DEBUG = False"


def test_rewind_multiple_steps(tmp_path: Path):
    """Rewind 2 steps → both files reverted."""
    mgr = CheckpointManager(tmp_path, session_id="test")
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    snap1 = mgr.snapshot_files(["a.py"])
    f1.write_text("a = 1")
    mgr.save("write_file", {"path": "a.py"}, {"ok": True}, True, snap1)
    snap2 = mgr.snapshot_files(["b.py"])
    f2.write_text("b = 2")
    mgr.save("write_file", {"path": "b.py"}, {"ok": True}, True, snap2)
    assert f1.exists() and f2.exists()
    mgr.rewind(2)
    assert not f1.exists()
    assert not f2.exists()


def test_rewind_non_file_tool(tmp_path: Path):
    """Tool call without file changes (search, shell) → checkpoint saved, rewind pops it."""
    mgr = CheckpointManager(tmp_path, session_id="test")
    mgr.save(
        tool_name="search_code",
        tool_args={"query": "test"},
        tool_result={"ok": True, "output": "found"},
        tool_ok=True,
    )
    assert mgr.count() == 1
    undone = mgr.rewind(1)
    assert len(undone) == 1
    assert undone[0].tool_name == "search_code"
    assert mgr.count() == 0


def test_checkpoint_rotation(tmp_path: Path):
    """max_checkpoints=3 → 4th checkpoint deletes 1st."""
    mgr = CheckpointManager(tmp_path, session_id="test", max_checkpoints=3)
    for i in range(4):
        f = tmp_path / f"f{i}.py"
        snap = mgr.snapshot_files([f"f{i}.py"])
        f.write_text(f"x = {i}")
        mgr.save("write_file", {"path": f"f{i}.py"}, {"ok": True}, True, snap)
    assert mgr.count() == 3
    cps = mgr.list_checkpoints()
    assert cps[0]["id"] == 2  # first checkpoint (id=1) should be rotated out


def test_list_checkpoints(tmp_path: Path):
    """List checkpoints returns ordered list with tool info."""
    mgr = CheckpointManager(tmp_path, session_id="test")
    f = tmp_path / "test.py"
    snap = mgr.snapshot_files(["test.py"])
    f.write_text("x = 1")
    mgr.save("write_file", {"path": "test.py", "content": "x = 1"}, {"ok": True}, True, snap)
    cps = mgr.list_checkpoints()
    assert len(cps) == 1
    assert cps[0]["tool"] == "write_file"
    assert cps[0]["changes"] == 1


def test_rewind_no_checkpoints(tmp_path: Path):
    """Rewind with no checkpoints → empty list."""
    mgr = CheckpointManager(tmp_path, session_id="test")
    undone = mgr.rewind(5)
    assert undone == []


def test_clear(tmp_path: Path):
    """Clear removes all checkpoints."""
    mgr = CheckpointManager(tmp_path, session_id="test")
    mgr.save("shell", {"cmd": "ls"}, {"ok": True}, True)
    mgr.save("shell", {"cmd": "pwd"}, {"ok": True}, True)
    assert mgr.count() == 2
    mgr.clear()
    assert mgr.count() == 0
