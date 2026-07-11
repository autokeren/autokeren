from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from autokeren.config import Config
from autokeren.memory import MemoryManager
from autokeren.tools.collaborate import CollaborateTool
from autokeren.models.base import ModelResponse


@patch("autokeren.agent.Agent.run")
def test_collaborate_tool(mock_run: MagicMock, tmp_path: Path) -> None:
    # Setup mock responses: Coder returns code, Critic returns APPROVED
    mock_run.side_effect = [
        ModelResponse(content="def hello():\n    return 'world'"),
        ModelResponse(content="APPROVED"),
    ]

    cfg = Config()
    memory = MemoryManager(str(tmp_path))
    tool = CollaborateTool(cfg, str(tmp_path), memory)

    res = tool.run(task="Buat fungsi hello world", max_turns=2)
    assert res.ok is True
    assert "Sesi kolaborasi multi-agent selesai" in res.output
    assert "APPROVED" in res.output
    assert "hello()" in res.output
