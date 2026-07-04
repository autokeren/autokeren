"""Tests for autokeren session manager."""
from __future__ import annotations

from pathlib import Path

import pytest

from autokeren.session import SessionManager


@pytest.fixture()
def session_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SessionManager:
    monkeypatch.setenv("AUTOKEREN_CONFIG_DIR", str(tmp_path))
    return SessionManager(str(tmp_path / "project"))


class TestSessionManager:
    def test_save_creates_file(self, session_manager: SessionManager) -> None:
        sid = session_manager.save("my session", [{"role": "user", "content": "hi"}], {"total": 10})
        assert sid
        sessions = session_manager.list()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "my session"

    def test_save_sanitizes_filename(self, session_manager: SessionManager) -> None:
        sid = session_manager.save("../../etc/passwd", [{"role": "user", "content": "hi"}], {})
        assert sid
        sessions = session_manager.list()
        assert len(sessions) == 1
        # name is still stored as-is inside the JSON
        assert sessions[0]["name"] == "../../etc/passwd"

    def test_load_by_name(self, session_manager: SessionManager) -> None:
        session_manager.save("test session", [{"role": "user", "content": "hi"}], {"total": 10})
        data = session_manager.load("test session")
        assert data is not None
        assert data["name"] == "test session"
        assert data["messages"][0]["content"] == "hi"

    def test_load_by_id(self, session_manager: SessionManager) -> None:
        sid = session_manager.save("named", [{"role": "user"}], {})
        data = session_manager.load(sid)
        assert data is not None
        assert data["id"] == sid

    def test_load_not_found(self, session_manager: SessionManager) -> None:
        assert session_manager.load("missing") is None

    def test_list_sorted(self, session_manager: SessionManager) -> None:
        session_manager.save("older", [{"role": "user"}], {})
        session_manager.save("newer", [{"role": "assistant"}], {})
        sessions = session_manager.list()
        assert len(sessions) == 2
        assert sessions[0]["name"] == "newer"

    def test_delete(self, session_manager: SessionManager) -> None:
        session_manager.save("to delete", [{"role": "user"}], {})
        assert session_manager.delete("to delete") is True
        assert session_manager.list() == []

    def test_delete_not_found(self, session_manager: SessionManager) -> None:
        assert session_manager.delete("missing") is False
