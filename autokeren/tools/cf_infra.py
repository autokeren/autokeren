"""Cloudflare infrastructure tools — KV + D1 via Cloudflare API."""
from __future__ import annotations

from typing import Any

import httpx

from autokeren.tools.base import Tool, ToolResult


def _cf_get(account_id: str, api_token: str, path: str, timeout: float = 30) -> dict:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}{path}"
    r = httpx.get(url, headers={"Authorization": f"Bearer {api_token}"}, timeout=timeout)
    data = r.json()
    if not data.get("success"):
        errors = data.get("errors", [])
        raise RuntimeError(f"Cloudflare API error: {errors}")
    return data.get("result", {})


def _cf_post(account_id: str, api_token: str, path: str, body: Any = None, timeout: float = 30) -> dict:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}{path}"
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    data = r.json()
    if not data.get("success"):
        errors = data.get("errors", [])
        raise RuntimeError(f"Cloudflare API error: {errors}")
    return data.get("result", {})


def _cf_put(account_id: str, api_token: str, path: str, content: str, timeout: float = 30) -> dict:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}{path}"
    r = httpx.put(
        url,
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "text/plain"},
        content=content,
        timeout=timeout,
    )
    data = r.json()
    if not data.get("success"):
        errors = data.get("errors", [])
        raise RuntimeError(f"Cloudflare API error: {errors}")
    return data.get("result", {})


class CloudflareKVTool(Tool):
    name = "cf_kv"
    description = (
        "Operasi Cloudflare KV: get, put, list keys, list namespaces. "
        "Butuh account_id + api_token di config."
    )
    requires_permission = True
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["get", "put", "list_keys", "list_namespaces"],
                "description": "Aksi KV.",
            },
            "namespace_id": {"type": "string", "description": "KV namespace ID (untuk get/put/list_keys)."},
            "key": {"type": "string", "description": "KV key (untuk get/put)."},
            "value": {"type": "string", "description": "KV value (untuk put)."},
        },
        "required": ["action"],
    }

    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg

    def run(self, action: str, namespace_id: str = "", key: str = "", value: str = "", **_) -> ToolResult:
        acct = self.cfg.cloudflare.account_id
        token = self.cfg.cloudflare.api_token
        if not acct or not token:
            return ToolResult(error="Cloudflare account_id/api_token belum diisi", ok=False)
        try:
            if action == "list_namespaces":
                result = _cf_get(acct, token, "/storage/kv/namespaces")
                ns_list = [{"id": ns.get("id", ""), "title": ns.get("title", "")} for ns in result if isinstance(result, list)]
                return ToolResult(output=ns_list)

            if not namespace_id:
                return ToolResult(error="namespace_id wajib untuk get/put/list_keys", ok=False)

            if action == "list_keys":
                result = _cf_get(acct, token, f"/storage/kv/namespaces/{namespace_id}/keys")
                keys = [k.get("name", "") for k in result if isinstance(result, list)]
                return ToolResult(output=keys)

            if action == "get":
                if not key:
                    return ToolResult(error="key wajib untuk get", ok=False)
                url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/storage/kv/namespaces/{namespace_id}/values/{key}"
                r = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
                if r.status_code != 200:
                    return ToolResult(error=f"KV get error: {r.status_code} {r.text[:200]}", ok=False)
                return ToolResult(output=r.text)

            if action == "put":
                if not key:
                    return ToolResult(error="key wajib untuk put", ok=False)
                _cf_put(acct, token, f"/storage/kv/namespaces/{namespace_id}/values/{key}", value)
                return ToolResult(output=f"KV put: {key} = {value[:80]}")

            return ToolResult(error=f"action tidak dikenal: {action}", ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

    def permission_desc(self, action: str = "", namespace_id: str = "", key: str = "", **_) -> str:
        if action == "put":
            return f"KV put: {key} di namespace {namespace_id}"
        return f"KV {action}"


class CloudflareD1Tool(Tool):
    name = "cf_d1"
    description = (
        "Query Cloudflare D1 database. "
        "Action: query (SELECT), exec (INSERT/UPDATE/DDL), list (list databases)."
    )
    requires_permission = True
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["query", "exec", "list"],
                "description": "Aksi D1.",
            },
            "database_id": {"type": "string", "description": "D1 database ID (untuk query/exec)."},
            "sql": {"type": "string", "description": "SQL statement (untuk query/exec)."},
        },
        "required": ["action"],
    }

    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg

    def run(self, action: str, database_id: str = "", sql: str = "", **_) -> ToolResult:
        acct = self.cfg.cloudflare.account_id
        token = self.cfg.cloudflare.api_token
        if not acct or not token:
            return ToolResult(error="Cloudflare account_id/api_token belum diisi", ok=False)
        try:
            if action == "list":
                result = _cf_get(acct, token, "/d1/database")
                dbs = [{"id": db.get("uuid", ""), "name": db.get("name", "")} for db in result if isinstance(result, list)]
                return ToolResult(output=dbs)

            if not database_id:
                return ToolResult(error="database_id wajib untuk query/exec", ok=False)
            if not sql:
                return ToolResult(error="sql wajib untuk query/exec", ok=False)

            result = _cf_post(
                acct, token,
                f"/d1/database/{database_id}/query",
                body={"sql": sql},
            )

            if isinstance(result, list):
                # Multiple statements
                summaries = []
                for r in result:
                    meta = r.get("meta", {})
                    rows = r.get("results", [])
                    summaries.append({
                        "changes": meta.get("changes", 0),
                        "rows_read": meta.get("rows_read", len(rows)),
                        "rows": rows[:50],
                    })
                return ToolResult(output=summaries)
            elif isinstance(result, dict):
                meta = result.get("meta", {})
                rows = result.get("results", [])
                return ToolResult(output={
                    "changes": meta.get("changes", 0),
                    "rows_read": meta.get("rows_read", len(rows)),
                    "rows": rows[:100],
                })

            return ToolResult(output=str(result))
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

    def permission_desc(self, action: str = "", database_id: str = "", sql: str = "", **_) -> str:
        if action == "exec":
            return f"D1 exec: {sql[:60]} di database {database_id}"
        return f"D1 {action}"
