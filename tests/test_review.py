"""Tests for Cross-Model Review — selector + parser."""
from __future__ import annotations

from autokeren.review.selector import ReviewerSelector
from autokeren.review.parser import parse_review_output, format_review_for_agent


def test_selector_different_vendor():
    """Coder kimi-code → reviewer glm-5.2 (beda vendor)."""
    sel = ReviewerSelector()
    assert sel.select("kimi-code") == "glm-5.2"
    assert sel.select("glm-5.2") == "kimi-code"
    assert sel.select("kimi-2.6") == "glm-flash"


def test_selector_different_vendor_full_id():
    """Full model ID dengan @cf/ prefix."""
    sel = ReviewerSelector()
    reviewer = sel.select("@cf/moonshotai/kimi-k2.7-code")
    assert reviewer != "kimi-code"
    assert "glm" in reviewer


def test_selector_is_different_vendor():
    """is_different_vendor returns True untuk beda model."""
    sel = ReviewerSelector()
    assert sel.is_different_vendor("kimi-code", "glm-5.2") is True
    assert sel.is_different_vendor("kimi-code", "kimi-code") is False


def test_parse_no_issues():
    """Reviewer bilang NO ISSUES → approved=True."""
    result = parse_review_output("NO ISSUES FOUND", "glm-5.2")
    assert result.approved is True
    assert len(result.issues) == 0
    assert result.reviewer_model == "glm-5.2"


def test_parse_critical_issue():
    """Parse critical issue dengan file + line + fix."""
    raw = """SEVERITY: CRITICAL
ISSUE: SQL injection di login function
FILE: src/login.py:42
FIX: Gunakan parameterized query
"""
    result = parse_review_output(raw, "glm-5.2")
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity == "CRITICAL"
    assert "SQL injection" in issue.description
    assert issue.file == "src/login.py"
    assert issue.line == 42
    assert "parameterized" in issue.fix
    assert result.critical_count == 1
    assert result.approved is False


def test_parse_multiple_issues():
    """Parse multiple issues dari review output."""
    raw = """SEVERITY: CRITICAL
ISSUE: Hardcoded API key
FILE: config.py:10
FIX: Move to env var

SEVERITY: LOW
ISSUE: Missing docstring
FILE: utils.py:5
FIX: Add docstring
"""
    result = parse_review_output(raw, "glm-5.2")
    assert len(result.issues) == 2
    assert result.critical_count == 1
    assert result.approved is False


def test_format_review_for_agent():
    """Format review untuk agent consumption."""
    result = parse_review_output("NO ISSUES FOUND", "glm-5.2")
    formatted = format_review_for_agent(result)
    assert "NO ISSUES FOUND" in formatted
    assert "glm-5.2" in formatted
