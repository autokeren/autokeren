"""Camofox e2e automation tool (wraps existing bridge)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import now_iso


class CamofoxTool(Tool):
    name = "camofox"
    description = "Control Camofox browser for end-to-end testing and web interaction."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "snapshot", "click", "type", "eval", "screenshot", "assert", "net_start", "net_get", "console_get"],
                "description": "Camofox action to perform.",
            },
            "url": {"type": "string"},
            "selector": {"type": "string"},
            "ref": {"type": "integer"},
            "text": {"type": "string"},
            "expression": {"type": "string"},
            "press_enter": {"type": "boolean", "default": False},
            "assertion": {"type": "object"},
            "profile": {"type": "string"},
        },
        "required": ["action"],
    }

    def __init__(self, cfg: Any):
        self.cfg = cfg

    def needs_permission(self, action: str = "", **_) -> bool:
        return action in ("click", "type", "eval")

    def permission_desc(self, action: str = "", **_) -> str:
        return f"camofox {action}"

    def run(self, action: str, **kwargs) -> ToolResult:
        profile = kwargs.get("profile") or self.cfg.camofox.default_profile
        user_id = self.cfg.camofox.user_id
        bridge = os.path.expanduser("~/.hermes/scripts/camofox_bridge_v2.py")
        base = [sys.executable, bridge, "--profile", profile, "--user", user_id, "--session", "autokeren"]
        try:
            if action == "navigate":
                return self._run(base + ["nav", kwargs.get("url", "https://example.com")])
            if action == "snapshot":
                return self._run(base + ["snap"])
            if action == "click":
                extra = []
                if kwargs.get("ref"):
                    extra = ["--ref", str(kwargs["ref"])]
                elif kwargs.get("selector"):
                    extra = ["--selector", kwargs["selector"]]
                return self._run(base + ["click"] + extra)
            if action == "type":
                extra = []
                if kwargs.get("ref"):
                    extra = ["--ref", str(kwargs["ref"])]
                elif kwargs.get("selector"):
                    extra = ["--selector", kwargs["selector"]]
                if kwargs.get("press_enter"):
                    extra.append("--enter")
                return self._run(base + ["type", kwargs.get("text", "")] + extra)
            if action == "eval":
                return self._run(base + ["eval", kwargs.get("expression", "")])
            if action == "screenshot":
                path = kwargs.get("save_path") or f"/tmp/autokeren-camofox-{now_iso()}.png"
                r = self._run(base + ["screenshot", "--save", path])
                r.output = r.output or {"screenshot_path": path}
                if isinstance(r.output, dict):
                    r.output["screenshot_path"] = path
                return r
            if action == "net_start":
                return self._run(base + ["net", "start"])
            if action == "net_get":
                return self._run(base + ["net", "get"])
            if action == "console_get":
                return self._run(base + ["console", "get"])
            if action == "assert":
                assertion = kwargs.get("assertion", {})
                kind = assertion.get("kind", "visible_text")
                value = assertion.get("value", "")
                if kind == "visible_text":
                    expr = f"document.body.innerText.includes({json.dumps(value)})"
                    r = self._run(base + ["eval", expr])
                    try:
                        parsed = json.loads(r.output) if isinstance(r.output, str) else {}
                        ok = parsed.get("result") is True
                    except Exception:
                        ok = value in (r.output or "")
                    return ToolResult(output=f"assert visible_text '{value}': {ok}", ok=ok)
                if kind == "selector":
                    expr = f"!!document.querySelector({json.dumps(value)})"
                    r = self._run(base + ["eval", expr])
                    try:
                        parsed = json.loads(r.output) if isinstance(r.output, str) else {}
                        ok = parsed.get("result") is True
                    except Exception:
                        ok = False
                    return ToolResult(output=f"assert selector '{value}': {ok}", ok=ok)
                return ToolResult(error=f"unknown assertion kind: {kind}", ok=False)
            return ToolResult(error=f"unknown camofox action: {action}", ok=False)
        except Exception as e:
            return ToolResult(error=f"camofox error: {e}", ok=False)

    def _run(self, cmd: list[str]) -> ToolResult:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return ToolResult(
            output=result.stdout or result.stderr,
            error=None if result.returncode == 0 else f"exit code {result.returncode}",
            ok=result.returncode == 0,
        )
