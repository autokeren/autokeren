"""Tests for Ghost Agent manager."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from autokeren.ghost.manager import GhostAgentInfo, GhostManager


class MockTmux:
    def __init__(self):
        self.active_sessions = set()

    def run(self, args, **kwargs):
        mock = MagicMock()
        cmd = args[0]
        subcmd = args[1]
        if cmd == "tmux":
            if subcmd == "has-session":
                # tmux has-session -t session_name
                t_idx = args.index("-t") if "-t" in args else 2
                target = args[t_idx + 1]
                mock.returncode = 0 if target in self.active_sessions else 1
            elif subcmd == "new-session":
                # tmux new-session -d -s session_name
                s_idx = args.index("-s")
                target = args[s_idx + 1]
                self.active_sessions.add(target)
                mock.returncode = 0
            elif subcmd == "kill-session":
                # tmux kill-session -t session_name
                t_idx = args.index("-t")
                target = args[t_idx + 1]
                if target in self.active_sessions:
                    self.active_sessions.remove(target)
                mock.returncode = 0
            else:
                mock.returncode = 0
        else:
            mock.returncode = 0
        return mock


def test_ghost_agent_info_is_running():
    info = GhostAgentInfo(id=1, task="test", status="running", started_at=100.0)
    assert info.is_running
    assert info.runtime > 0


def test_ghost_agent_info_completed():
    info = GhostAgentInfo(id=1, task="test", status="completed", started_at=100.0)
    assert not info.is_running
    assert info.runtime == 0.0


def test_ghost_agent_info_to_dict():
    info = GhostAgentInfo(id=1, task="test task", status="running", started_at=100.0)
    d = info.to_dict()
    assert d["id"] == 1
    assert d["status"] == "running"
    assert "task" in d
    assert "runtime" in d


def test_ghost_spawn(tmp_path):
    mock_tmux = MockTmux()
    with patch("autokeren.ghost.manager.subprocess.run", side_effect=mock_tmux.run):
        gm = GhostManager(project_root=str(tmp_path), max_agents=3)
        info = gm.spawn("fix bug di login.py")
        assert info.status == "running"
        assert info.id == 1
        assert len(gm.list_agents()) == 1


def test_ghost_spawn_max_limit(tmp_path):
    mock_tmux = MockTmux()
    with patch("autokeren.ghost.manager.subprocess.run", side_effect=mock_tmux.run):
        gm = GhostManager(project_root=str(tmp_path), max_agents=2)
        gm.spawn("task 1")
        gm.spawn("task 2")
        try:
            gm.spawn("task 3")
            assert False, "Should raise RuntimeError"
        except RuntimeError as e:
            assert "Maksimal" in str(e)


def test_ghost_kill(tmp_path):
    mock_tmux = MockTmux()
    with patch("autokeren.ghost.manager.subprocess.run", side_effect=mock_tmux.run):
        gm = GhostManager(project_root=str(tmp_path))
        info = gm.spawn("test task")
        assert f"ak-ghost-{info.id}" in mock_tmux.active_sessions
        result = gm.kill(info.id)
        assert result
        assert info.status == "killed"
        assert f"ak-ghost-{info.id}" not in mock_tmux.active_sessions


def test_ghost_kill_nonexistent(tmp_path):
    gm = GhostManager(project_root=str(tmp_path))
    assert gm.kill(999) is False


def test_ghost_check_status_running(tmp_path):
    mock_tmux = MockTmux()
    with patch("autokeren.ghost.manager.subprocess.run", side_effect=mock_tmux.run):
        gm = GhostManager(project_root=str(tmp_path))
        info = gm.spawn("test")
        status = gm.check_status(info.id)
        assert status == "running"


def test_ghost_check_status_completed(tmp_path):
    mock_tmux = MockTmux()  # Empty active sessions
    with patch("autokeren.ghost.manager.subprocess.run", side_effect=mock_tmux.run):
        gm = GhostManager(project_root=str(tmp_path))
        info = GhostAgentInfo(id=1, task="test", status="running", started_at=100.0)
        gm._agents[1] = info
        status = gm.check_status(1)
        assert status == "completed"


def test_ghost_check_status_unknown(tmp_path):
    gm = GhostManager(project_root=str(tmp_path))
    assert gm.check_status(999) == "unknown"


def test_ghost_active_count(tmp_path):
    mock_tmux = MockTmux()
    with patch("autokeren.ghost.manager.subprocess.run", side_effect=mock_tmux.run):
        gm = GhostManager(project_root=str(tmp_path), max_agents=3)
        assert gm.active_count == 0
        gm.spawn("task 1")
        gm.spawn("task 2")
        assert gm.active_count == 2


def test_ghost_get_output(tmp_path):
    log_file = tmp_path / ".ak-ghost-1.log"
    log_file.write_text("ghost output log")
    gm = GhostManager(project_root=str(tmp_path))
    info = GhostAgentInfo(id=1, task="test", status="running", started_at=100.0, log_file=str(log_file))
    gm._agents[1] = info
    output = gm.get_output(1)
    assert "ghost output" in output


def test_ghost_get_output_no_log(tmp_path):
    gm = GhostManager(project_root=str(tmp_path))
    assert gm.get_output(999) == ""


def test_ghost_spawn_avoids_existing_tmux_sessions(tmp_path):
    mock_tmux = MockTmux()
    mock_tmux.active_sessions.add("ak-ghost-1")  # Simulate ak-ghost-1 is occupied
    
    with patch("autokeren.ghost.manager.subprocess.run", side_effect=mock_tmux.run):
        gm = GhostManager(project_root=str(tmp_path))
        info = gm.spawn("task with existing session")
        assert info.id == 2
        assert info.status == "running"
        assert "ak-ghost-2" in mock_tmux.active_sessions
