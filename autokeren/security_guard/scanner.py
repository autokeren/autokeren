"""Security scanner — scan files untuk secrets, SQLi, XSS, auth, deps."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass
class SecurityFinding:
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    description: str
    file: str
    line: int | None = None
    match: str = ""
    fix: str = ""


class Checker(Protocol):
    def check(self, file_path: str, content: str) -> list[SecurityFinding]: ...


_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'(?:api[_-]?key|apikey)["\s]*[:=]\s*["\']([\w]{32,})["\']', "API key terdeteksi"),
    (r'(?:secret|token)["\s]*[:=]\s*["\']([\w]{32,})["\']', "Secret/token terdeteksi"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID terdeteksi"),
    (r'aws_secret_access_key["\s]*[:=]\s*["\']([A-Za-z0-9/+=]{40})["\']', "AWS Secret Key terdeteksi"),
    (r'gh[pousr]_[A-Za-z0-9]{36}', "GitHub token terdeteksi"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private key terdeteksi"),
    (r'password["\s]*[:=]\s*["\']([^"\']{8,})["\']', "Hardcoded password terdeteksi"),
]


class SecretChecker:
    def check(self, file_path: str, content: str) -> list[SecurityFinding]:
        if file_path.endswith((".env.example", ".env.sample")):
            return []
        findings: list[SecurityFinding] = []
        for pattern, desc in _SECRET_PATTERNS:
            for m in re.finditer(pattern, content, re.I):
                line = content[: m.start()].count("\n") + 1
                findings.append(SecurityFinding(
                    severity="CRITICAL",
                    category="secret_exposure",
                    description=desc,
                    file=file_path,
                    line=line,
                    match=m.group(0)[:50] + "...",
                    fix="Pindahkan ke environment variable. Jangan hardcode di source code.",
                ))
        return findings


_Sqli_PATTERNS: list[tuple[str, str]] = [
    (r'(?:SELECT|INSERT|UPDATE|DELETE|WHERE).*["\']\s*\+\s*\w', "SQL query dengan string concatenation"),
    (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|WHERE).*\{', "SQL query dengan f-string (injection risk)"),
    (r'\.format\(.*(?:SELECT|INSERT|UPDATE|DELETE|WHERE)', "SQL query dengan .format() (injection risk)"),
]


class SQLiChecker:
    def check(self, file_path: str, content: str) -> list[SecurityFinding]:
        if not _is_code_file(file_path, content):
            return []
        findings: list[SecurityFinding] = []
        for pattern, desc in _Sqli_PATTERNS:
            for m in re.finditer(pattern, content, re.I):
                line = content[: m.start()].count("\n") + 1
                findings.append(SecurityFinding(
                    severity="HIGH",
                    category="sqli",
                    description=desc,
                    file=file_path,
                    line=line,
                    fix="Gunakan parameterized query atau ORM method.",
                ))
        unsafe_exec = re.findall(r'\.execute\(\s*["\']((?:SELECT|INSERT|UPDATE|DELETE)[^"\']*)["\']', content, re.I)
        for match in unsafe_exec:
            if "?" not in match and "%s" not in match and ":" not in match:
                line = content[: content.index(match)].count("\n") + 1
                findings.append(SecurityFinding(
                    severity="HIGH",
                    category="sqli",
                    description=".execute() dengan raw SQL string tanpa parameterization",
                    file=file_path,
                    line=line,
                    fix="Gunakan parameterized query: execute(sql, params)",
                ))
        return findings


_XSS_PATTERNS: list[tuple[str, str]] = [
    (r'dangerouslySetInnerHTML', "dangerouslySetInnerHTML — XSS risk"),
    (r'\.innerHTML\s*=', ".innerHTML assignment — XSS risk"),
    (r'document\.write\(', "document.write() — XSS risk"),
    (r'v-html', "v-html — XSS risk"),
]


class XSSChecker:
    def check(self, file_path: str, content: str) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        for pattern, desc in _XSS_PATTERNS:
            for m in re.finditer(pattern, content):
                line = content[: m.start()].count("\n") + 1
                findings.append(SecurityFinding(
                    severity="MEDIUM",
                    category="xss",
                    description=desc,
                    file=file_path,
                    line=line,
                    fix="Sanitize user input sebelum render. Gunakan textContent atau DOMPurify.",
                ))
        return findings


_FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r'\beval\s*\(', "eval() dilarang — security risk"),
    (r'\bFunction\s*\(', "new Function() dilarang — security risk"),
    (r'\bsetTimeout\s*\(\s*["\']', "setTimeout dengan string — code injection risk"),
    (r'\bsetInterval\s*\(\s*["\']', "setInterval dengan string — code injection risk"),
]


class ForbiddenCodeChecker:
    def check(self, file_path: str, content: str) -> list[SecurityFinding]:
        if not _is_code_file(file_path, content):
            return []
        findings: list[SecurityFinding] = []
        for pattern, desc in _FORBIDDEN_PATTERNS:
            for m in re.finditer(pattern, content):
                line = content[: m.start()].count("\n") + 1
                findings.append(SecurityFinding(
                    severity="HIGH",
                    category="forbidden_code",
                    description=desc,
                    file=file_path,
                    line=line,
                    fix="Hindari eval/Function/setTimeout(string). Gunakan function reference.",
                ))
        return findings


def _is_code_file(file_path: str, content: str) -> bool:
    return file_path.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"))


class SecurityScanner:
    """Orchestrate all security checkers."""

    def __init__(self, checks: list[str] | None = None) -> None:
        all_checkers: dict[str, Checker] = {
            "secrets": SecretChecker(),
            "sqli": SQLiChecker(),
            "xss": XSSChecker(),
            "forbidden": ForbiddenCodeChecker(),
        }
        active = checks or list(all_checkers.keys())
        self.checkers = [all_checkers[c] for c in active if c in all_checkers]

    def scan(self, file_path: str, content: str) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        for checker in self.checkers:
            findings.extend(checker.check(file_path, content))
        return findings

    def scan_file(self, path: str) -> list[SecurityFinding]:
        try:
            from pathlib import Path
            p = Path(path)
            if not p.exists() or not p.is_file():
                return []
            content = p.read_text(encoding="utf-8", errors="replace")
            return self.scan(str(p), content)
        except Exception:
            return []

    @staticmethod
    def format_findings(findings: list[SecurityFinding]) -> str:
        if not findings:
            return "✓ Tidak ada security issues ditemukan."
        critical = sum(1 for f in findings if f.severity == "CRITICAL")
        high = sum(1 for f in findings if f.severity == "HIGH")
        lines = [f"🛡️ Security Scan — {len(findings)} findings ({critical} CRITICAL, {high} HIGH)\n"]
        for f in findings:
            lines.append(
                f"  [{f.severity}] {f.category} — {f.file}:{f.line or '?'}\n"
                f"    {f.description}\n"
                f"    Fix: {f.fix}"
            )
        return "\n".join(lines)
