"""Camofox e2e automation tool (REST API direct client)."""
from __future__ import annotations

import base64
import json
import os
from typing import Any
import requests  # type: ignore[import-untyped]

from autokeren.tools.base import Tool, ToolResult
from autokeren.utils import now_iso

BASE_URL = os.environ.get("CAMOFOX_URL", "http://localhost:9377")
STATE_PATH = os.path.expanduser("~/.config/autokeren/camofox_sessions.json")


class CamofoxTool(Tool):
    name = "camofox"
    description = (
        "Control Camofox browser server for end-to-end testing and web interaction. "
        "Operates directly on the REST API of a running Camofox server."
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
        self.user_id = getattr(self.cfg.camofox, "user_id", "ajat")
        self.session_key = "autokeren"
        self.default_profile = getattr(self.cfg.camofox, "default_profile", "default")
        self.tab_id: str | None = None

    def needs_permission(self, action: str = "", **_) -> bool:
        return action in ("click", "type", "eval")

    def permission_desc(self, action: str = "", **_) -> str:
        return f"camofox {action}"

    def _state_key(self, profile: str) -> str:
        return f"{self.user_id}::{self.session_key}::{profile}"

    def _load_tab_id(self, profile: str) -> str | None:
        if not os.path.exists(STATE_PATH):
            return None
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(self._state_key(profile), {}).get("tab_id")
        except Exception:
            return None

    def _save_tab_id(self, profile: str, tab_id: str | None) -> None:
        try:
            data = {}
            if os.path.exists(STATE_PATH):
                with open(STATE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            
            os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
            data[self._state_key(profile)] = {
                "tab_id": tab_id,
                "userId": self.user_id,
                "profile": profile,
                "updated_at": now_iso(),
            }
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _req(self, method: str, path: str, body: dict | None = None, is_raw: bool = False) -> Any:
        url = f"{BASE_URL}{path}"
        try:
            if method == "GET":
                r = requests.get(url, timeout=30)
            elif method == "DELETE":
                r = requests.delete(url, timeout=30)
            else:
                r = requests.post(url, json=body, timeout=30)
            
            if is_raw:
                return r
            return r.json() if r.text else {}
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Gagal tersambung ke Camofox Browser Server di {BASE_URL}. "
                "Pastikan kontainer docker Camofox atau server lokal Anda sudah berjalan (node server.js)."
            )
        except Exception as e:
            return {"_error": str(e)}

    def _ensure_tab(self, profile: str, url: str = "https://example.com") -> str:
        tab_id = self._load_tab_id(profile)
        if tab_id:
            # Validasi apakah tab masih aktif di server
            st = self._req("GET", f"/tabs?userId={self.user_id}")
            if isinstance(st, dict) and "tabs" in st:
                ids = [t.get("tabId") for t in st["tabs"]]
                if tab_id in ids:
                    self.tab_id = tab_id
                    return tab_id
            
        # Buat tab baru jika tidak ada
        payload = {
            "url": url,
            "userId": self.user_id,
            "sessionKey": self.session_key,
        }
        if profile and profile != "default":
            payload["profile"] = profile
        r = self._req("POST", "/tabs", payload)
        new_id = r.get("tabId")
        if not new_id:
            raise RuntimeError(f"Gagal mendapatkan tabId dari Camofox: {r}")
        self.tab_id = new_id
        self._save_tab_id(profile, new_id)
        return new_id

    def run(self, action: str, **kwargs) -> ToolResult:
        profile = kwargs.get("profile") or self.default_profile
        try:
            tab_id = self._ensure_tab(profile, kwargs.get("url", "https://example.com"))
            
            if action == "navigate":
                url = kwargs.get("url", "https://example.com")
                r = self._req("POST", f"/tabs/{tab_id}/navigate", {
                    "url": url,
                    "userId": self.user_id,
                })
                # Beri jeda loading halus
                import time
                time.sleep(2)
                return ToolResult(output=r)

            if action == "snapshot":
                offset = kwargs.get("offset")
                q = f"?userId={self.user_id}&includeScreenshot=true"
                if offset:
                    q += f"&offset={offset}"
                r = self._req("GET", f"/tabs/{tab_id}/snapshot{q}")
                return ToolResult(output=r)

            if action == "click":
                p = {"userId": self.user_id}
                if kwargs.get("ref"):
                    p["ref"] = kwargs["ref"]
                elif kwargs.get("selector"):
                    p["selector"] = kwargs["selector"]
                r = self._req("POST", f"/tabs/{tab_id}/click", p)
                return ToolResult(output=r)

            if action == "type":
                p = {
                    "userId": self.user_id,
                    "text": kwargs.get("text", ""),
                    "pressEnter": kwargs.get("press_enter", False)
                }
                if kwargs.get("ref"):
                    p["ref"] = kwargs["ref"]
                elif kwargs.get("selector"):
                    p["selector"] = kwargs["selector"]
                r = self._req("POST", f"/tabs/{tab_id}/type", p)
                return ToolResult(output=r)

            if action == "eval":
                r = self._req("POST", f"/tabs/{tab_id}/evaluate", {
                    "expression": kwargs.get("expression", ""),
                    "userId": self.user_id,
                })
                return ToolResult(output=r)

            if action == "screenshot":
                save_path = kwargs.get("save_path") or f"/tmp/autokeren-camofox-{now_iso()}.png"
                r = self._req("GET", f"/tabs/{tab_id}/screenshot?userId={self.user_id}", is_raw=True)
                if isinstance(r, dict) and "_error" in r:
                    return ToolResult(error=r["_error"], ok=False)
                if r.status_code != 200:
                    return ToolResult(error=r.text, ok=False)
                
                with open(save_path, "wb") as f:
                    f.write(r.content)
                
                return ToolResult(output={
                    "bytes": len(r.content),
                    "base64": base64.b64encode(r.content).decode(),
                    "screenshot_path": os.path.abspath(save_path)
                })

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
                r = self._req("POST", f"/tabs/{tab_id}/evaluate", {
                    "expression": script,
                    "userId": self.user_id,
                })
                return ToolResult(output=r)

            if action == "net_get":
                r = self._req("POST", f"/tabs/{tab_id}/evaluate", {
                    "expression": "JSON.stringify(window.__networkLogs || [])",
                    "userId": self.user_id,
                })
                try:
                    logs = json.loads(r.get("result", "[]"))
                    return ToolResult(output={"logs": logs, "count": len(logs)})
                except Exception:
                    return ToolResult(output=r)

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
                r = self._req("POST", f"/tabs/{tab_id}/evaluate", {
                    "expression": script,
                    "userId": self.user_id,
                })
                try:
                    logs = json.loads(r.get("result", "[]"))
                    return ToolResult(output={"logs": logs, "count": len(logs)})
                except Exception:
                    return ToolResult(output=r)

            if action == "assert":
                assertion = kwargs.get("assertion", {})
                kind = assertion.get("kind", "visible_text")
                value = assertion.get("value", "")
                if kind == "visible_text":
                    expr = f"document.body.innerText.includes({json.dumps(value)})"
                    r = self._req("POST", f"/tabs/{tab_id}/evaluate", {
                        "expression": expr,
                        "userId": self.user_id,
                    })
                    ok = r.get("result") is True
                    return ToolResult(output=f"assert visible_text '{value}': {ok}", ok=ok)
                if kind == "selector":
                    expr = f"!!document.querySelector({json.dumps(value)})"
                    r = self._req("POST", f"/tabs/{tab_id}/evaluate", {
                        "expression": expr,
                        "userId": self.user_id,
                    })
                    ok = r.get("result") is True
                    return ToolResult(output=f"assert selector '{value}': {ok}", ok=ok)
                return ToolResult(error=f"unknown assertion kind: {kind}", ok=False)

            return ToolResult(error=f"unknown action: {action}", ok=False)
        except RuntimeError as re:
            return ToolResult(error=str(re), ok=False)
        except Exception as e:
            return ToolResult(error=f"camofox error: {e}", ok=False)
