"""Tests for Ghost Agent manager."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from autokeren.ghost.manager import GhostAgentInfo, GhostManager


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


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_spawn(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    gm = GhostManager(project_root=str(tmp_path), max_agents=3)
    info = gm.spawn("fix bug di login.py")
    assert info.status == "running"
    assert info.id == 1
    assert len(gm.list_agents()) == 1
    assert mock_run.call_count == 2


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_spawn_max_limit(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    gm = GhostManager(project_root=str(tmp_path), max_agents=2)
    gm.spawn("task 1")
    gm.spawn("task 2")
    try:
        gm.spawn("task 3")
        assert False, "Should raise RuntimeError"
    except RuntimeError as e:
        assert "Maksimal" in str(e)


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_kill(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    gm = GhostManager(project_root=str(tmp_path))
    info = gm.spawn("test task")
    result = gm.kill(info.id)
    assert result
    assert info.status == "killed"


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_kill_nonexistent(tmp_path):
    gm = GhostManager(project_root=str(tmp_path))
    assert gm.kill(999) is False


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_check_status_running(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    gm = GhostManager(project_root=str(tmp_path))
    info = gm.spawn("test")
    status = gm.check_status(info.id)
    assert status == "running"


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_check_status_completed(mock_run, tmp_path):
    gm = GhostManager(project_root=str(tmp_path))
    info = GhostAgentInfo(id=1, task="test", status="running", started_at=100.0)
    gm._agents[1] = info
    mock_run.return_value = MagicMock(returncode=1)
    status = gm.check_status(1)
    assert status == "completed"


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_check_status_unknown(tmp_path):
    gm = GhostManager(project_root=str(tmp_path))
    assert gm.check_status(999) == "unknown"


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_active_count(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    gm = GhostManager(project_root=str(tmp_path), max_agents=3)
    assert gm.active_count == 0
    gm.spawn("task 1")
    gm.spawn("task 2")
    assert gm.active_count == 2


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_get_output(mock_run, tmp_path):
    log_file = tmp_path / ".ak-ghost-1.log"
    log_file.write_text("ghost output log")
    gm = GhostManager(project_root=str(tmp_path))
    info = GhostAgentInfo(id=1, task="test", status="running", started_at=100.0, log_file=str(log_file))
    gm._agents[1] = info
    output = gm.get_output(1)
    assert "ghost output" in output


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_get_output_no_log(mock_run, tmp_path):
    gm = GhostManager(project_root=str(tmp_path))
    assert gm.get_output(999) == ""


@patch("autokeren.ghost.manager.subprocess.run")
def test_ghost_spawn_avoids_existing_tmux_sessions(mock_run, tmp_path):
    def side_effect(args, **kwargs):
        cmd = args[0]
        subcmd = args[1]
        if cmd == "tmux" and subcmd == "has-session":
            target = args[3]
            if target == "ak-ghost-1":
                return MagicMock(returncode=0)
            elif target == "ak-ghost-2":
                return MagicMock(returncode=1)
        return MagicMock(returncode=0)

    mock_run.side_effect = side_effect
    gm = GhostManager(project_root=str(tmp_path))
    info = gm.spawn("task with existing session")
    assert info.id == 2
    assert info.status == "running"
