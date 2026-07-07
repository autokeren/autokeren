"""Tests for Loop Breaker — error tracking, pattern detection."""
from __future__ import annotations

from autokeren.loop.detector import LoopBreaker
from autokeren.loop.patterns import PatternDetector, ToolCallEntry


def test_loop_detection_same_error():
    """3x same error → trigger loop break."""
    lb = LoopBreaker(max_repeats=3)
    a1 = lb.track_error("SyntaxError at /app/main.py:10", "write_file")
    a2 = lb.track_error("SyntaxError at /app/main.py:10", "write_file")
    a3 = lb.track_error("SyntaxError at /app/main.py:10", "write_file")
    assert a1.action == "continue"
    assert a2.action == "continue"
    assert a3.action == "break"


def test_loop_detection_different_error():
    """3x different errors → no trigger."""
    lb = LoopBreaker(max_repeats=3)
    lb.track_error("Error A", "write_file")
    lb.track_error("Error B", "write_file")
    a3 = lb.track_error("Error C", "write_file")
    assert a3.action == "continue"


def test_loop_detection_normalized():
    """Same error dengan path/line berbeda → detected as same."""
    lb = LoopBreaker(max_repeats=3)
    lb.track_error("Error at /app/v1/main.py:10", "shell")
    lb.track_error("Error at /app/v2/main.py:20", "shell")
    a3 = lb.track_error("Error at /app/v3/main.py:30", "shell")
    assert a3.action == "break"


def test_loop_break_switch_model():
    """Loop break triggers switch_model flag."""
    lb = LoopBreaker(max_repeats=2, auto_switch_model=True)
    lb.track_error("Same error", "write_file")
    action = lb.track_error("Same error", "write_file")
    assert action.action == "break"
    assert action.switch_model is True


def test_loop_break_context_clear():
    """Context clear only triggers at max_repeats + 2."""
    lb = LoopBreaker(max_repeats=2, auto_clear_context=True)
    lb.track_error("E", "t")
    lb.track_error("E", "t")
    a3 = lb.track_error("E", "t")
    assert a3.clear_context is False  # 3 repeats, need 4
    a4 = lb.track_error("E", "t")
    assert a4.clear_context is True  # 4 repeats >= 2+2


def test_loop_reset():
    """Reset clears history."""
    lb = LoopBreaker(max_repeats=3)
    lb.track_error("E", "t")
    lb.track_error("E", "t")
    lb.reset()
    assert len(lb.history) == 0


def test_pattern_same_tool_same_args():
    """Same tool + same args 3x → detected."""
    pd = PatternDetector()
    for _ in range(3):
        pd.track(ToolCallEntry(name="read_file", args={"path": "a.py"}, success=True))
    result = pd.detect()
    assert result.detected
    assert result.pattern == "same_tool_same_args"


def test_pattern_write_test_fail_cycle():
    """Write → test → fail → write cycle detected."""
    pd = PatternDetector()
    pd.track(ToolCallEntry(name="write_file", args={"path": "a.py"}, success=True))
    pd.track(ToolCallEntry(name="run_shell", args={"cmd": "npm test"}, success=False))
    pd.track(ToolCallEntry(name="write_file", args={"path": "a.py"}, success=True))
    pd.track(ToolCallEntry(name="run_shell", args={"cmd": "npm test"}, success=False))
    pd.track(ToolCallEntry(name="write_file", args={"path": "a.py"}, success=True))
    result = pd.detect()
    assert result.detected
    assert result.pattern == "write_test_fail_cycle"


def test_pattern_file_thrashing():
    """Read file A → B → A → B → detected."""
    pd = PatternDetector()
    for path in ["a.py", "b.py", "a.py", "b.py"]:
        pd.track(ToolCallEntry(name="read_file", args={"path": path}, success=True))
    result = pd.detect()
    assert result.detected
    assert result.pattern == "file_thrashing"


def test_pattern_no_loop():
    """Diverse tool calls → no pattern."""
    pd = PatternDetector()
    pd.track(ToolCallEntry(name="read_file", args={"path": "a.py"}, success=True))
    pd.track(ToolCallEntry(name="write_file", args={"path": "b.py"}, success=True))
    pd.track(ToolCallEntry(name="run_shell", args={"cmd": "ls"}, success=True))
    result = pd.detect()
    assert not result.detected


def test_pattern_apology_loop():
    """Agent keeps saying 'now I understand' → detected."""
    pd = PatternDetector()
    for msg in ["Now I understand the issue", "Let me try a different approach", "Ah, I see the problem"]:
        pd.track(ToolCallEntry(name="write_file", args={"path": "x"}, success=False, message=msg))
    result = pd.detect()
    assert result.detected
    assert result.pattern == "apology_loop"
