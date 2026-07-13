"""Tests for FDDM tool integration."""
from __future__ import annotations

from unittest.mock import MagicMock

from autokeren.tools.base import ToolResult
from autokeren.tools.fddm import FDDMTool


def test_fddm_tool_schema():
    tool = FDDMTool()
    schema = tool.schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "fddm"
    assert "action" in schema["function"]["parameters"]["properties"]
    assert "emit" in schema["function"]["parameters"]["properties"]["action"]["enum"]


def test_fddm_tool_defaults():
    tool = FDDMTool()
    assert "workers.dev" in tool.base_url


def test_fddm_tool_custom_url():
    tool = FDDMTool(base_url="https://custom.example.com")
    assert tool.base_url == "https://custom.example.com"


def test_fddm_emit_mock():
    tool = FDDMTool()
    tool._post = MagicMock(return_value=ToolResult(output={"scent_id": "scent_123", "dimensions": 384}))
    result = tool.run(action="emit", type="error", text="test error", emitter_id="agent_test")
    assert result.ok
    assert isinstance(result.output, dict)
    assert result.output["scent_id"] == "scent_123"


def test_fddm_sniff_mock():
    tool = FDDMTool()
    tool._post = MagicMock(
        return_value=ToolResult(output=[{"scent_id": "s1", "type": "error", "score": 0.8, "similarity": 0.9, "artifact": "test"}])
    )
    result = tool.run(action="sniff", text="test query")
    assert result.ok
    assert isinstance(result.output, list)
    assert len(result.output) == 1


def test_fddm_stats_mock():
    tool = FDDMTool()
    tool._get = MagicMock(return_value=ToolResult(output={"total_scents": 5, "archived": 0, "emitters": 2}))
    result = tool.run(action="stats")
    assert result.ok
    assert result.output["total_scents"] == 5


def test_fddm_error_handling():
    tool = FDDMTool()
    tool._post = MagicMock(return_value=ToolResult(error="FDDM error: Connection failed", ok=False))
    result = tool.run(action="emit", type="error", text="test")
    assert not result.ok
    assert "FDDM error" in (result.error or "")


def test_fddm_unknown_action():
    tool = FDDMTool()
    result = tool.run(action="unknown_action")
    assert not result.ok
    assert "tidak dikenal" in (result.error or "")
# ak:4ef8d33039e55e8c
