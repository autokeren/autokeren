import subprocess
from pathlib import Path
from autokeren.tools.tmux import TmuxTool


def test_tmux_tool_permission():
    tool = TmuxTool(Path("/tmp"))
    assert tool.needs_permission("run")
    assert tool.needs_permission("kill")
    assert not tool.needs_permission("capture")
    assert not tool.needs_permission("sniff")


def test_tmux_tool_sniff_clean(monkeypatch):
    class MockCompletedProcess:
        returncode = 0
        stdout = "server running on port 3000\nall connections successful\n"
        stderr = ""

    def mock_run(args, **kwargs):
        return MockCompletedProcess()

    monkeypatch.setattr(subprocess, "run", mock_run)

    tool = TmuxTool(Path("/tmp"))
    res = tool.run(action="sniff")
    assert res.ok
    assert "Logs are clean" in res.output


def test_tmux_tool_sniff_with_errors(monkeypatch):
    class MockCompletedProcess:
        returncode = 0
        stdout = (
            "server running on port 3000\n"
            "TypeError: Cannot read property 'id' of undefined\n"
            "at Object.handleRequest (server.js:42:15)\n"
        )
        stderr = ""

    def mock_run(args, **kwargs):
        return MockCompletedProcess()

    monkeypatch.setattr(subprocess, "run", mock_run)

    tool = TmuxTool(Path("/tmp"))
    res = tool.run(action="sniff")
    assert not res.ok
    assert "TypeError: Cannot read property 'id' of undefined" in res.output
