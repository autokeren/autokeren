"""Tests for Live Architecture Enforcement."""
from __future__ import annotations

from pathlib import Path

from autokeren.enforcer.engine import EnforcementEngine
from autokeren.enforcer.rules import load_rules, generate_default_rules


def _write_rules(tmp_path: Path, content: str) -> Path:
    p = tmp_path / ".ak-rules.yaml"
    p.write_text(content)
    return p


def test_enforce_max_file_lines_block(tmp_path: Path):
    """File > 500 lines → blocked."""
    rules = _write_rules(tmp_path, """
rules:
  max_file_lines:
    limit: 10
    action: block
    message: "File terlalu panjang: {limit} baris"
""")
    engine = EnforcementEngine(rules)
    long_content = "\n".join(f"line {i}" for i in range(20))
    result = engine.check_before_write("big.py", long_content)
    assert result.blocked
    assert any("panjang" in v.message for v in result.violations)


def test_enforce_max_file_lines_ok(tmp_path: Path):
    """File <= limit → no violation."""
    rules = _write_rules(tmp_path, """
rules:
  max_file_lines:
    limit: 100
    action: block
""")
    engine = EnforcementEngine(rules)
    result = engine.check_before_write("small.py", "print('hello')\n")
    assert not result.blocked


def test_enforce_no_eval_block(tmp_path: Path):
    """eval() → blocked."""
    rules = _write_rules(tmp_path, """
rules:
  no_eval:
    forbid_patterns:
      - "\\\\beval\\\\s*\\\\("
    action: block
    message: "eval() dilarang"
""")
    engine = EnforcementEngine(rules)
    result = engine.check_before_write("script.js", "result = eval(expression)")
    assert result.blocked
    assert any("eval" in v.message for v in result.violations)


def test_enforce_warn_only(tmp_path: Path):
    """action=warn → not blocked, but warning present."""
    rules = _write_rules(tmp_path, """
rules:
  no_console:
    forbid_patterns:
      - "console\\\\.log"
    action: warn
    message: "console.log di production"
""")
    engine = EnforcementEngine(rules)
    result = engine.check_before_write("app.js", "console.log('debug')")
    assert not result.blocked
    assert len(result.warnings) == 1


def test_enforce_no_rules_file(tmp_path: Path):
    """No .ak-rules.yaml → no rules, no violations."""
    engine = EnforcementEngine(tmp_path / ".ak-rules.yaml")
    result = engine.check_before_write("anything.py", "eval('bad')")
    assert not result.blocked
    assert engine.has_rules() is False


def test_enforce_multiple_violations(tmp_path: Path):
    """Multiple rules violated → multiple violations."""
    rules = _write_rules(tmp_path, """
rules:
  max_file_lines:
    limit: 5
    action: block
  no_eval:
    forbid_patterns:
      - "\\\\beval\\\\s*\\\\("
    action: block
""")
    engine = EnforcementEngine(rules)
    content = "\n".join(f"line {i}" for i in range(10)) + "\neval('bad')"
    result = engine.check_before_write("bad.py", content)
    assert result.blocked
    assert len(result.violations) >= 2


def test_generate_default_rules(tmp_path: Path):
    """generate_default_rules creates valid YAML."""
    (tmp_path / "package.json").write_text("{}")
    yaml_text = generate_default_rules(tmp_path)
    rules_path = _write_rules(tmp_path, yaml_text)
    rules = load_rules(rules_path)
    assert len(rules) >= 2
    names = [r.name for r in rules]
    assert "max_file_lines" in names
    assert "no_eval" in names
