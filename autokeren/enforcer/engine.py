"""Enforcement engine — check files against rules before write."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from autokeren.enforcer.rules import Rule, load_rules


@dataclass
class Violation:
    rule: str
    action: str
    message: str
    file: str


@dataclass
class EnforcementResult:
    violations: list[Violation] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(v.action == "block" for v in self.violations)

    @property
    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.action == "warn"]


class EnforcementEngine:
    """Check files against rules sebelum write."""

    def __init__(self, rules_path: Path) -> None:
        self.rules = load_rules(rules_path)
        self.rules_path = rules_path

    def check_before_write(self, file_path: str, content: str) -> EnforcementResult:
        result = EnforcementResult()
        for rule in self.rules:
            violation = self._check_rule(rule, file_path, content)
            if violation:
                result.violations.append(violation)
        return result

    def _check_rule(self, rule: Rule, file_path: str, content: str) -> Violation | None:
        if rule.rule_type == "max_file_lines":
            line_count = content.count("\n") + 1
            if rule.limit > 0 and line_count > rule.limit:
                msg = rule.message.format(limit=rule.limit, actual=line_count) or f"File {line_count} baris > {rule.limit}"
                return Violation(rule=rule.name, action=rule.action, message=msg, file=file_path)

        elif rule.rule_type == "pattern_matching" or rule.rule_type == "forbidden":
            for pattern in rule.forbid_patterns:
                if re.search(pattern, content):
                    msg = rule.message or f"Pattern terlarang: {pattern}"
                    return Violation(rule=rule.name, action=rule.action, message=msg, file=file_path)

        elif rule.rule_type == "imports":
            for forbidden in rule.forbid:
                if forbidden in content:
                    msg = rule.message or f"Import terlarang: {forbidden}"
                    return Violation(rule=rule.name, action=rule.action, message=msg, file=file_path)

        return None

    def has_rules(self) -> bool:
        return len(self.rules) > 0

    def rule_count(self) -> int:
        return len(self.rules)
