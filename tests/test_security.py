"""Tests for Vibe-Security Guard."""
from __future__ import annotations

from autokeren.security_guard.scanner import SecurityScanner


def test_secret_detection_api_key():
    """Hardcoded API key → CRITICAL finding."""
    scanner = SecurityScanner(checks=["secrets"])
    findings = scanner.scan("config.py", 'api_key = "sk_fake_1234567890abcdefghijklmnopqrstuv"')
    assert len(findings) >= 1
    assert findings[0].severity == "CRITICAL"
    assert "API key" in findings[0].description


def test_secret_detection_aws_key():
    """AWS Access Key → CRITICAL finding."""
    scanner = SecurityScanner(checks=["secrets"])
    findings = scanner.scan("config.py", "aws_access = 'AKIAIOSFODNN7EXAMPLE'")
    assert len(findings) >= 1
    assert findings[0].severity == "CRITICAL"


def test_secret_detection_github_token():
    """GitHub token → CRITICAL finding."""
    scanner = SecurityScanner(checks=["secrets"])
    findings = scanner.scan("config.py", 'token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"')
    assert any("GitHub" in f.description for f in findings)


def test_secret_detection_password():
    """Hardcoded password → CRITICAL finding."""
    scanner = SecurityScanner(checks=["secrets"])
    findings = scanner.scan("db.py", 'password = "supersecret123"')
    assert len(findings) >= 1
    assert "password" in findings[0].description.lower()


def test_secret_env_example_ok():
    """ .env.example → no findings (excluded)."""
    scanner = SecurityScanner(checks=["secrets"])
    findings = scanner.scan(".env.example", 'api_key = "sk_fake_1234567890abcdefghijklmnopqrstuv"')
    assert len(findings) == 0


def test_sqli_string_concat():
    """SQL with string concat → HIGH finding."""
    scanner = SecurityScanner(checks=["sqli"])
    content = 'query = "SELECT * FROM users WHERE name = " + name'
    findings = scanner.scan("db.py", content)
    assert len(findings) >= 1
    assert findings[0].severity == "HIGH"


def test_sqli_fstring():
    """SQL with f-string → HIGH finding."""
    scanner = SecurityScanner(checks=["sqli"])
    content = 'query = f"SELECT * FROM users WHERE id = {user_id}"'
    findings = scanner.scan("db.py", content)
    assert len(findings) >= 1


def test_sqli_parameterized_ok():
    """Parameterized query → no finding."""
    scanner = SecurityScanner(checks=["sqli"])
    content = 'cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))'
    findings = scanner.scan("db.py", content)
    assert len(findings) == 0


def test_xss_innerhtml():
    """innerHTML assignment → MEDIUM finding."""
    scanner = SecurityScanner(checks=["xss"])
    findings = scanner.scan("app.js", "element.innerHTML = userInput")
    assert len(findings) >= 1
    assert findings[0].severity == "MEDIUM"


def test_xss_dangerously_set_inner_html():
    """dangerouslySetInnerHTML → MEDIUM finding."""
    scanner = SecurityScanner(checks=["xss"])
    findings = scanner.scan("component.jsx", "<div dangerouslySetInnerHTML={{__html: data}} />")
    assert len(findings) >= 1


def test_forbidden_eval():
    """eval() → HIGH finding."""
    scanner = SecurityScanner(checks=["forbidden"])
    findings = scanner.scan("script.js", "result = eval(expression)")
    assert len(findings) >= 1
    assert findings[0].severity == "HIGH"


def test_scan_all_checkers():
    """All checkers run together."""
    scanner = SecurityScanner()
    content = """
api_key = "sk_fake_1234567890abcdefghijklmnopqrstuv"
element.innerHTML = userInput
eval("malicious code")
"""
    findings = scanner.scan("app.py", content)
    categories = {f.category for f in findings}
    assert "secret_exposure" in categories
    assert "xss" in categories
    assert "forbidden_code" in categories


def test_format_findings_empty():
    """No findings → success message."""
    result = SecurityScanner.format_findings([])
    assert "Tidak ada" in result


def test_format_findings_with_issues():
    """Findings → formatted output."""
    scanner = SecurityScanner(checks=["secrets"])
    findings = scanner.scan("config.py", 'api_key = "sk_fake_1234567890abcdefghijklmnopqrstuv"')
    result = SecurityScanner.format_findings(findings)
    assert "CRITICAL" in result
    assert "config.py" in result
