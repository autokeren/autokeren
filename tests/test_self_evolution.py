"""Unit tests for the Self-Evolution and Self-Refactoring loop."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from autokeren.agent import Agent
from autokeren.config import Config
from autokeren.tools import ToolRegistry


def test_agent_run_self_improvement() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create mock tool path
        tools_dir = root / "autokeren" / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        mock_tool_file = tools_dir / "calculator.py"
        mock_tool_file.write_text("# Mock calculator tool\n", encoding="utf-8")
        
        # Setup mock Agent dependencies
        cfg = Config()
        tools = MagicMock(spec=ToolRegistry)
        
        agent = Agent(cfg, tools, str(root))
        
        # Mock run_autonomous
        agent.run_autonomous = MagicMock(return_value={"reflection_summary": "Fixed!"})
        
        with patch("autokeren.cli.build_registry") as mock_build_reg:
            mock_new_registry = MagicMock(spec=ToolRegistry)
            mock_build_reg.return_value = mock_new_registry
            
            # Trigger self improvement
            success = agent.run_self_improvement(
                failed_tool_name="calculator",
                error_message="ZeroDivisionError",
                tool_args={"a": 5, "b": 0}
            )
            
            # Assertions
            assert success is True
            agent.run_autonomous.assert_called_once()
            args, kwargs = agent.run_autonomous.call_args
            assert "Perbaiki bug/keterbatasan pada tool 'calculator'" in args[0]
            assert "ZeroDivisionError" in kwargs["context"]
            
            # Verify hot-reload of registry
            mock_build_reg.assert_called_once()
            assert agent.tools == mock_new_registry
