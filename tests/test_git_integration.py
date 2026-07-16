import subprocess
from autokeren.tools.git import GitAutoCommitTool
from autokeren.agent import Agent
from autokeren.config import Config
from autokeren.tools import ToolRegistry

def test_git_auto_commit_tool(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path)
    
    f = tmp_path / "foo.py"
    f.write_text("print('hello')", encoding="utf-8")
    
    tool = GitAutoCommitTool(tmp_path)
    res = tool.run(files=["foo.py"], summary="add print hello")
    assert res.ok
    
    log_res = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=tmp_path, capture_output=True, text=True)
    assert "feat: add print hello" in log_res.stdout

def test_agent_git_micro_commit(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path)
    
    init_file = tmp_path / "init.txt"
    init_file.write_text("init", encoding="utf-8")
    subprocess.run(["git", "add", "init.txt"], cwd=tmp_path)
    subprocess.run(["git", "commit", "-m", "chore: initial commit"], cwd=tmp_path)

    cfg = Config()
    cfg.autokeren.git_auto_commit.enabled = True
    
    class MockRouter:
        def complete(self, messages, **kwargs):
            from autokeren.models.base import ModelResponse
            return ModelResponse(content="feat(test): modify file")
    
    agent = Agent(cfg, ToolRegistry(), str(tmp_path))
    agent.router = MockRouter()
    
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1", encoding="utf-8")
    
    agent._run_git_micro_commit("test.py")
    
    log_res = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=tmp_path, capture_output=True, text=True)
    assert "feat(test): modify file" in log_res.stdout

def test_agent_git_rollback(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path)
    
    init_file = tmp_path / "init.txt"
    init_file.write_text("init", encoding="utf-8")
    subprocess.run(["git", "add", "init.txt"], cwd=tmp_path)
    subprocess.run(["git", "commit", "-m", "chore: initial commit"], cwd=tmp_path)
    
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1", encoding="utf-8")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path)
    subprocess.run(["git", "commit", "-m", "feat(test): add test file"], cwd=tmp_path)
    
    cfg = Config()
    cfg.autokeren.git_auto_commit.enabled = True
    
    agent = Agent(cfg, ToolRegistry(), str(tmp_path))
    
    from autokeren.loop.detector import LoopAction
    class MockLoopBreaker:
        def track_error(self, **kwargs):
            return LoopAction(action="break", suggestion="stop", switch_model=False, clear_context=False)
        def reset(self):
            pass
            
    agent.loop_breaker = MockLoopBreaker()
    
    lb_action = agent.loop_breaker.track_error(error="failure", tool_name="run_shell", context={})
    if lb_action.action == "break":
        if agent._git_auto_commit_enabled:
            rollback_res = subprocess.run(
                ["git", "-C", agent.project_root, "reset", "--hard", "HEAD~1"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert rollback_res.returncode == 0
            
    assert not test_file.exists()
