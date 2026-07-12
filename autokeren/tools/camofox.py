"""Camofox e2e automation tool (Go-Rod IPC client)."""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Callable

from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import now_iso


class CamofoxTool(Tool):
    name = "camofox"
    description = (
        "Control native Go-Rod browser automation client for end-to-end testing and web interaction."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate", "snapshot", "click", "type", "eval", 
                    "screenshot", "assert", "net_start", "net_get", "console_get"
                ],
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
            "save_path": {"type": "string"},
        },
        "required": ["action"],
    }

    def __init__(self, cfg: Any):
        self.cfg = cfg
        self.rpc_callback: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None

    def set_rpc_callback(self, callback: Callable[[str, dict[str, Any]], dict[str, Any]]) -> None:
        self.rpc_callback = callback

    def needs_permission(self, action: str = "", **_) -> bool:
        return action in ("click", "type", "eval")

    def permission_desc(self, action: str = "", **_) -> str:
        return f"camofox {action}"

    def run(self, action: str, **kwargs) -> ToolResult:
        if not self.rpc_callback:
            return ToolResult(
                error="Go-Rod TUI browser client is not connected. This tool must run through the autokeren TUI environment.",
                ok=False
            )

        try:
            # Map action helpers
            if action == "net_start":
                script = """
                (function(){
                    if (window.__cf_interceptor) return 'already_active';
                    window.__networkLogs = [];
                    const origFetch = window.fetch;
                    window.fetch = async function(...args) {
                        const url = args[0];
                        const opts = args[1] || {};
                        const started = Date.now();
                        try {
                            const resp = await origFetch.apply(this, args);
                            window.__networkLogs.push({
                                type: 'fetch',
                                url: typeof url === 'string' ? url : url.url,
                                method: opts.method || 'GET',
                                status: resp.status,
                                statusText: resp.statusText,
                                time: started
                            });
                            return resp;
                        } catch (err) {
                            window.__networkLogs.push({
                                type: 'fetch',
                                url: typeof url === 'string' ? url : url.url,
                                method: opts.method || 'GET',
                                error: err.message,
                                time: started
                            });
                            throw err;
                        }
                    };
                    window.__cf_interceptor = true;
                    return 'interceptor_injected';
                })()
                """
                res = self.rpc_callback("eval", {"expression": script})
                return ToolResult(
                    output=res.get("output", ""),
                    error=res.get("error"),
                    ok=res.get("ok", True)
                )

            if action == "net_get":
                res = self.rpc_callback("eval", {"expression": "JSON.stringify(window.__networkLogs || [])"})
                if not res.get("ok", True):
                    return ToolResult(error=res.get("error"), ok=False)
                try:
                    out = res.get("output", {})
                    # Go-Rod returns: {"result": "..."} inside output
                    raw_result = out.get("result", "[]") if isinstance(out, dict) else "[]"
                    logs = json.loads(raw_result)
                    return ToolResult(output={"logs": logs, "count": len(logs)})
                except Exception as e:
                    return ToolResult(output=res.get("output"), error=str(e), ok=True)

            if action == "console_get":
                script = """
                (function(){
                    if (window.__cf_console_hook) return JSON.stringify(window.__consoleLogs || []);
                    window.__consoleLogs = [];
                    ['log','warn','error','info'].forEach(level => {
                        const orig = console[level];
                        console[level] = function(...args) {
                            window.__consoleLogs.push({
                                level: level,
                                time: Date.now(),
                                message: args.join(' ')
                            });
                            return orig.apply(this, args);
                        };
                    });
                    window.__cf_console_hook = true;
                    return JSON.stringify(window.__consoleLogs || []);
                })()
                """
                res = self.rpc_callback("eval", {"expression": script})
                if not res.get("ok", True):
                    return ToolResult(error=res.get("error"), ok=False)
                try:
                    out = res.get("output", {})
                    raw_result = out.get("result", "[]") if isinstance(out, dict) else "[]"
                    logs = json.loads(raw_result)
                    return ToolResult(output={"logs": logs, "count": len(logs)})
                except Exception as e:
                    return ToolResult(output=res.get("output"), error=str(e), ok=True)

            # Standard actions
            res = self.rpc_callback(action, kwargs)
            ok = res.get("ok", True)
            err_msg = res.get("error")
            output = res.get("output", "")

            # Post-process screenshot to write file locally
            if action == "screenshot" and ok:
                save_path = kwargs.get("save_path") or f"/tmp/autokeren-camofox-{now_iso()}.png"
                try:
                    if isinstance(output, dict) and "base64" in output:
                        img_bytes = base64.b64decode(output["base64"])
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, "wb") as f:
                            f.write(img_bytes)
                        output["screenshot_path"] = os.path.abspath(save_path)
                except Exception as e:
                    err_msg = f"Failed to save screenshot file locally: {e}"
                    ok = False

            return ToolResult(output=output, error=err_msg, ok=ok)

        except Exception as e:
            return ToolResult(error=f"camofox error: {e}", ok=False)
