"""Review output parser — parse LLM review output ke structured data."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ReviewIssue:
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    file: str
    line: int | None = None
    fix: str = ""


@dataclass
class ReviewResult:
    reviewer_model: str = ""
    issues: list[ReviewIssue] = field(default_factory=list)
    summary: str = ""
    raw_output: str = ""

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "HIGH")

    @property
    def approved(self) -> bool:
        return self.critical_count == 0 and self.high_count == 0


_SEVERITY_PATTERN = re.compile(
    r"SEVERITY:\s*(CRITICAL|HIGH|MEDIUM|LOW)", re.I
)
_ISSUE_PATTERN = re.compile(
    r"ISSUE:\s*(.+?)(?=\n(?:FILE:|SEVERITY:|Fix:|$))", re.DOTALL
)
_FILE_PATTERN = re.compile(
    r"FILE:\s*([^\s:]+)(?::(\d+))?", re.I
)
_FIX_PATTERN = re.compile(
    r"FIX:\s*(.+)", re.DOTALL
)


def parse_review_output(raw: str, reviewer_model: str = "") -> ReviewResult:
    """Parse review output ke ReviewResult."""
    if "NO ISSUES FOUND" in raw.upper():
        return ReviewResult(
            reviewer_model=reviewer_model,
            summary="No issues found",
            raw_output=raw,
        )
    issues: list[ReviewIssue] = []
    blocks = re.split(r"(?=SEVERITY:)", raw)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        sev_m = _SEVERITY_PATTERN.search(block)
        issue_m = _ISSUE_PATTERN.search(block)
        file_m = _FILE_PATTERN.search(block)
        fix_m = _FIX_PATTERN.search(block)
        if not sev_m or not issue_m:
            continue
        severity = sev_m.group(1).upper()
        description = issue_m.group(1).strip()
        file_path = file_m.group(1) if file_m else ""
        line_num = int(file_m.group(2)) if file_m and file_m.group(2) else None
        fix = fix_m.group(1).strip() if fix_m else ""
        fix = fix.split("\n")[0].strip() if fix else ""
        issues.append(ReviewIssue(
            severity=severity,
            description=description,
            file=file_path,
            line=line_num,
            fix=fix,
        ))
    return ReviewResult(
        reviewer_model=reviewer_model,
        issues=issues,
        summary=f"{len(issues)} issues found",
        raw_output=raw,
    )


def format_review_for_agent(result: ReviewResult) -> str:
    """Format review result untuk inject ke agent context."""
    if not result.issues:
        return f"Cross-model review by {result.reviewer_model}: NO ISSUES FOUND."
    lines = [f"Cross-model review by {result.reviewer_model}: {len(result.issues)} issues found\n"]
    for issue in result.issues:
        lines.append(
            f"[{issue.severity}] {issue.file}:{issue.line or '?'} — {issue.description}\n"
            f"  Fix: {issue.fix}"
        )
    if result.critical_count > 0:
        lines.append(f"\n{result.critical_count} CRITICAL issues — fix sebelum commit.")
    return "\n".join(lines)
