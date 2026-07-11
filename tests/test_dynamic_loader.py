"""Unit tests for the dynamic tool hot-loader."""
from __future__ import annotations

import tempfile
from pathlib import Path

from autokeren.config import Config
from autokeren.memory import MemoryManager
from autokeren.tools.base import ToolRegistry
from autokeren.tools.dynamic_loader import load_dynamic_tools


def test_load_dynamic_tools() -> None:
    # Set up temp project root
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        
        # Create config and memory mock
        cfg = Config()
        memory = MemoryManager(str(project_root))
        registry = ToolRegistry()
        
        # Call first time to initialize .ak-tools/ README
        load_dynamic_tools(project_root, registry, cfg, memory)
        
        dynamic_dir = project_root / ".ak-tools"
        assert dynamic_dir.exists()
        assert (dynamic_dir / "README.md").exists()
        
        # Write a dummy dynamic tool
        tool_code = (
            "from autokeren.tools.base import Tool, ToolResult\n\n"
            "class DummyDynamicTool(Tool):\n"
            "    name = 'dummy_dynamic'\n"
            "    description = 'A dummy dynamic tool'\n"
            "    parameters = {'type': 'object', 'properties': {}}\n\n"
            "    def __init__(self, project_root):\n"
            "        self.project_root = project_root\n\n"
            "    def run(self) -> ToolResult:\n"
            "        return ToolResult(output='dynamic success')\n"
        )
        (dynamic_dir / "dummy_tool.py").write_text(tool_code, encoding="utf-8")
        
        # Reload registry
        new_registry = ToolRegistry()
        load_dynamic_tools(project_root, new_registry, cfg, memory)
        
        # Assert tool is registered
        assert "dummy_dynamic" in new_registry.names()
        
        # Test tool runs
        tool = new_registry.get("dummy_dynamic")
        assert tool is not None
        res = new_registry.run("dummy_dynamic", {})
        assert res.ok
        assert res.output == "dynamic success"
