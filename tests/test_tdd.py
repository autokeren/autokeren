"""Unit tests for TDDEngine."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from autokeren.agent import Agent
from autokeren.multiagent.tdd import TDDEngine


class TestTDDEngine:
    def test_detect_environment_python_default(self, tmp_path: Path) -> None:
        mock_agent = MagicMock(spec=Agent)
        engine = TDDEngine(mock_agent, str(tmp_path), lambda x: None)
        env = engine.detect_environment()
        assert env["lang"] == "Python"
        assert "pytest" in env["test_runner"]

    def test_detect_environment_js(self, tmp_path: Path) -> None:
        mock_agent = MagicMock(spec=Agent)
        # Buat package.json palsu
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        engine = TDDEngine(mock_agent, str(tmp_path), lambda x: None)
        env = engine.detect_environment()
        assert env["lang"] == "JavaScript/TypeScript"
        assert env["test_runner"] == "npm test"

    def test_extract_code_markdown(self, tmp_path: Path) -> None:
        mock_agent = MagicMock(spec=Agent)
        engine = TDDEngine(mock_agent, str(tmp_path), lambda x: None)
        text = "Penjelasan:\n```python\nprint('hello')\n```\nSelesai."
        assert engine._extract_code(text) == "print('hello')"

    def test_extract_code_plain(self, tmp_path: Path) -> None:
        mock_agent = MagicMock(spec=Agent)
        engine = TDDEngine(mock_agent, str(tmp_path), lambda x: None)
        assert engine._extract_code("print('world')") == "print('world')"
