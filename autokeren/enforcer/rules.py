"""Rules parsing — load .ak-rules.yaml, generate defaults."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Rule:
    name: str
    rule_type: str  # max_file_lines, pattern_matching, forbidden, naming
    action: str = "warn"  # block | warn
    message: str = ""
    limit: int = 0
    pattern: str = ""
    forbid_patterns: list[str] = field(default_factory=list)
    require: list[str] = field(default_factory=list)
    forbid: list[str] = field(default_factory=list)


def load_rules(rules_path: Path) -> list[Rule]:
    if not rules_path.exists():
        return []
    data = yaml.safe_load(rules_path.read_text()) or {}
    rules_data = data.get("rules", {})
    rules: list[Rule] = []
    for name, cfg in rules_data.items():
        if not isinstance(cfg, dict):
            continue
        rule_type = _detect_type(name, cfg)
        rules.append(Rule(
            name=name,
            rule_type=rule_type,
            action=cfg.get("action", "warn"),
            message=cfg.get("message", ""),
            limit=cfg.get("limit", 0),
            pattern=cfg.get("pattern", ""),
            forbid_patterns=cfg.get("forbid_patterns", []),
            require=cfg.get("require", []) if isinstance(cfg.get("require"), list) else [],
            forbid=cfg.get("forbid", []) if isinstance(cfg.get("forbid"), list) else [],
        ))
    return rules


def _detect_type(name: str, cfg: dict[str, Any]) -> str:
    if "limit" in cfg:
        return "max_file_lines"
    if "forbid_patterns" in cfg:
        return "pattern_matching"
    if "forbid" in cfg or "require" in cfg:
        return "imports"
    if name == "no_eval" or "forbid_patterns" in cfg:
        return "forbidden"
    if "pattern" in cfg and cfg.get("pattern") in ("kebab-case", "snake_case", "camelCase", "PascalCase"):
        return "naming"
    return "pattern_matching"


def generate_default_rules(project_root: Path) -> str:
    has_js = (project_root / "package.json").exists()
    (project_root / "pyproject.toml").exists() or (project_root / "setup.py").exists()
    rules: dict[str, Any] = {"rules": {}}
    rules["rules"]["max_file_lines"] = {
        "limit": 500,
        "action": "warn",
        "message": "File melebihi {limit} baris. Split jadi multiple files.",
    }
    rules["rules"]["no_eval"] = {
        "forbid_patterns": [r"\beval\s*\(", r"\bFunction\s*\("],
        "action": "block",
        "message": "eval() dan new Function() dilarang — security risk",
    }
    if has_js:
        rules["rules"]["no_console_in_prod"] = {
            "forbid_patterns": [r"console\.log"],
            "action": "warn",
            "message": "console.log di production code",
        }
    return yaml.safe_dump(rules, sort_keys=False)
