"""Tests for autokeren tools, utils, memory, dan todo."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from autokeren.memory import MemoryManager
from autokeren.tools.base import Tool, ToolRegistry, ToolResult
from autokeren.tools.todo import TodoTool
from autokeren.utils import human_size, is_dangerous_command, redact, sanitize_filename


class _DummyTool(Tool):
    name = "dummy"
    description = "dummy tool for testing"
    parameters: dict[str, Any] = {}

    def run(self, **kwargs: Any) -> ToolResult:
        if kwargs.get("fail"):
            raise RuntimeError("boom")
        return ToolResult(output="dummy-ok")


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------


class TestToolResult:
    def test_to_dict_success(self) -> None:
        result = ToolResult(output="hello")
        assert result.to_dict() == {"ok": True, "output": "hello", "error": None}

    def test_to_dict_error(self) -> None:
        result = ToolResult(error="oops", ok=False)
        d = result.to_dict()
        assert d["ok"] is False
        assert d["output"] is None
        assert d["error"] == "oops"

    def test_to_dict_with_dict_output(self) -> None:
        result = ToolResult(output={"key": "val"})
        assert result.to_dict()["output"] == {"key": "val"}

    def test_ok_defaults_true(self) -> None:
        assert ToolResult().ok is True


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


class TestToolRegistry:
    def test_register_returns_self(self) -> None:
        registry = ToolRegistry()
        assert registry.register(_DummyTool()) is registry

    def test_get_registered(self) -> None:
        registry = ToolRegistry()
        tool = _DummyTool()
        registry.register(tool)
        assert registry.get("dummy") is tool

    def test_get_unknown_returns_none(self) -> None:
        registry = ToolRegistry()
        assert registry.get("nope") is None

    def test_run_unknown_tool(self) -> None:
        registry = ToolRegistry()
        result = registry.run("missing", {})
        assert result.ok is False
        assert "tidak ditemukan" in (result.error or "")

    def test_run_valid_tool(self) -> None:
        registry = ToolRegistry()
        registry.register(_DummyTool())
        result = registry.run("dummy", {})
        assert result.ok is True
        assert result.output == "dummy-ok"

    def test_run_catches_exception(self) -> None:
        registry = ToolRegistry()
        registry.register(_DummyTool())
        result = registry.run("dummy", {"fail": True})
        assert result.ok is False
        assert "RuntimeError" in (result.error or "")
        assert "boom" in (result.error or "")

    def test_names(self) -> None:
        registry = ToolRegistry()
        registry.register(_DummyTool())
        assert registry.names() == ["dummy"]

    def test_schemas(self) -> None:
        registry = ToolRegistry()
        registry.register(_DummyTool())
        schemas = registry.schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "dummy"


# ---------------------------------------------------------------------------
# is_dangerous_command
# ---------------------------------------------------------------------------


class TestIsDangerousCommand:
    def test_safe_command(self) -> None:
        ok, msg = is_dangerous_command("ls -la")
        assert ok is False
        assert msg == ""

    def test_rm_rf_root(self) -> None:
        ok, msg = is_dangerous_command("rm -rf /")
        assert ok is True
        assert "rm -rf /" in msg

    def test_case_insensitive(self) -> None:
        ok, _ = is_dangerous_command("MKFS.ext4 /dev/sda1")
        assert ok is True

    def test_custom_blocklist(self) -> None:
        ok, msg = is_dangerous_command("shutdown now", blocklist=["shutdown"])
        assert ok is True
        assert "shutdown" in msg

    def test_custom_blocklist_safe(self) -> None:
        ok, _ = is_dangerous_command("ls", blocklist=["shutdown"])
        assert ok is False


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_clean_name(self) -> None:
        assert sanitize_filename("hello") == "hello"

    def test_spaces_replaced(self) -> None:
        assert sanitize_filename("hello world") == "hello_world"

    def test_path_traversal_stripped(self) -> None:
        assert sanitize_filename("../etc/passwd") == "etc_passwd"

    def test_special_chars_replaced(self) -> None:
        assert sanitize_filename("a/b\\c*d") == "a_b_c_d"

    def test_keeps_dots_dashes(self) -> None:
        assert sanitize_filename("file-name.txt") == "file-name.txt"


# ---------------------------------------------------------------------------
# redact
# ---------------------------------------------------------------------------


class TestRedact:
    def test_none(self) -> None:
        assert redact(None) == ""

    def test_empty(self) -> None:
        assert redact("") == ""

    def test_short_value(self) -> None:
        assert redact("ab") == "***"

    def test_long_value_default_keep(self) -> None:
        assert redact("secret-token-12345") == "***2345"

    def test_custom_keep(self) -> None:
        assert redact("abcdefg", keep=2) == "***fg"


# ---------------------------------------------------------------------------
# human_size
# ---------------------------------------------------------------------------


class TestHumanSize:
    def test_bytes(self) -> None:
        assert human_size(0) == "0.0 B"
        assert human_size(512) == "512.0 B"

    def test_kilobytes(self) -> None:
        assert human_size(1024) == "1.0 KB"
        assert human_size(1536) == "1.5 KB"

    def test_megabytes(self) -> None:
        assert human_size(1048576) == "1.0 MB"

    def test_gigabytes(self) -> None:
        assert human_size(1073741824) == "1.0 GB"

    def test_terabytes(self) -> None:
        assert "TB" in human_size(1099511627776)


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------


@pytest.fixture()
def memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MemoryManager:
    monkeypatch.setenv("AUTOKEREN_CONFIG_DIR", str(tmp_path))
    return MemoryManager("/tmp/myproject")


class TestMemoryManager:
    def test_init_does_not_create_file(self, memory: MemoryManager) -> None:
        assert memory.exists() is False
        assert memory.load() == ""
        assert memory.line_count() == 0

    def test_save_and_load(self, memory: MemoryManager) -> None:
        memory.save("line one\nline two")
        assert memory.exists() is True
        assert memory.load() == "line one\nline two"
        assert memory.line_count() == 2

    def test_save_overwrites(self, memory: MemoryManager) -> None:
        memory.save("old content")
        memory.save("new content")
        assert memory.load() == "new content"

    def test_append_creates_section(self, memory: MemoryManager) -> None:
        content = memory.append("Build", "use npm")
        assert "## Build" in content
        assert "- use npm" in content
        assert memory.load() == content.rstrip("\n")

    def test_append_to_existing_section(self, memory: MemoryManager) -> None:
        memory.append("Build", "use npm")
        content = memory.append("Build", "run tests")
        assert "- use npm" in content
        assert "- run tests" in content

    def test_append_multiple_sections(self, memory: MemoryManager) -> None:
        memory.append("Build", "use npm")
        memory.append("Debug", "check logs")
        loaded = memory.load()
        assert "## Build" in loaded
        assert "## Debug" in loaded
        assert "- use npm" in loaded
        assert "- check logs" in loaded

    def test_clear(self, memory: MemoryManager) -> None:
        memory.save("something important")
        assert memory.exists() is True
        memory.clear()
        assert memory.load() == ""

    def test_get_path(self, memory: MemoryManager) -> None:
        path = memory.get_path()
        assert path.name == "memory.md"
        assert "projects" in path.parts


# ---------------------------------------------------------------------------
# TodoTool
# ---------------------------------------------------------------------------


class TestTodoTool:
    def test_list_empty(self) -> None:
        tool = TodoTool()
        result = tool.run(action="list")
        assert result.ok is True
        assert result.output == "todo list kosong"

    def test_add_requires_content(self) -> None:
        tool = TodoTool()
        result = tool.run(action="add")
        assert result.ok is False
        assert "content" in (result.error or "")

    def test_add_and_list(self) -> None:
        tool = TodoTool()
        result = tool.run(action="add", content="tulis dokumentasi")
        assert result.ok is True
        assert "tulis dokumentasi" in str(result.output)
        assert "pending" in str(result.output)

        listed = tool.run(action="list")
        assert listed.ok is True
        assert "tulis dokumentasi" in str(listed.output)

    def test_update_status(self) -> None:
        tool = TodoTool()
        tool.run(action="add", content="task satu")
        result = tool.run(action="update", index=1, status="completed")
        assert result.ok is True
        assert "completed" in str(result.output)
        assert tool.get_todos()[0]["status"] == "completed"

    def test_update_invalid_index(self) -> None:
        tool = TodoTool()
        result = tool.run(action="update", index=1, status="completed")
        assert result.ok is False
        assert "tidak valid" in (result.error or "")

    def test_update_zero_index(self) -> None:
        tool = TodoTool()
        tool.run(action="add", content="task")
        result = tool.run(action="update", index=0, status="completed")
        assert result.ok is False

    def test_clear(self) -> None:
        tool = TodoTool()
        tool.run(action="add", content="task satu")
        tool.run(action="add", content="task dua")
        assert len(tool.get_todos()) == 2

        result = tool.run(action="clear")
        assert result.ok is True
        assert "dikosongkan" in str(result.output)
        assert tool.get_todos() == []

    def test_unknown_action(self) -> None:
        tool = TodoTool()
        result = tool.run(action="magic")
        assert result.ok is False
        assert "tidak dikenal" in (result.error or "")

    def test_get_todos_returns_copy(self) -> None:
        tool = TodoTool()
        tool.run(action="add", content="task")
        todos = tool.get_todos()
        todos.clear()
        assert len(tool.get_todos()) == 1
