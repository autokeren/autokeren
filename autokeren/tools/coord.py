"""Coordination tools — claim/lease, release, dan merge queue untuk koordinasi antar-agent."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from autokeren.coord.store import CoordStore
from autokeren.tools.base import Tool, ToolResult


def _default_agent_id() -> str:
    return os.environ.get("AUTOKEREN_AGENT_ID", "").strip() or "main"


def _as_path_list(paths: Any) -> list[str]:
    if isinstance(paths, str):
        return [paths]
    return [str(p) for p in paths]


def _dump(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


class ClaimFilesTool(Tool):
    name = "claim_files"
    description = (
        "Claim/lease file SEBELUM diedit supaya tidak tabrakan dengan agent lain yang sedang "
        "mengerjakan file sama. Claim multi-path bersifat atomik. Lease punya TTL dan auto-expire; "
        "panggil release_claim setelah selesai edit. Jika path dipegang agent lain, respons berisi "
        "pemilik, sisa TTL, dan opsi wait (masuk antrian FIFO)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Path file relatif project root yang akan diedit (semua di-claim atomik).",
            },
            "agent_id": {"type": "string", "description": "Identitas agent; default env AUTOKEREN_AGENT_ID atau 'main'."},
            "ttl_seconds": {
                "type": "number",
                "description": "TTL lease dalam detik; lease auto-expire setelah TTL (default 300).",
            },
            "branch": {"type": "string", "description": "Branch konteks claim (opsional)."},
            "wait": {
                "type": "boolean",
                "description": "Jika true dan path konflik, request masuk antrian FIFO dan dipromosikan otomatis saat lease bebas.",
            },
        },
        "required": ["paths"],
    }

    def __init__(self, project_root: Path | str) -> None:
        self.store = CoordStore(project_root)

    def run(
        self,
        paths: Any,
        agent_id: str | None = None,
        ttl_seconds: float = 300,
        branch: str | None = None,
        wait: bool = False,
        **_: Any,
    ) -> ToolResult:
        try:
            result = self.store.claim(
                _as_path_list(paths),
                agent_id=str(agent_id).strip() if agent_id else _default_agent_id(),
                ttl_seconds=float(ttl_seconds),
                branch=branch,
                wait=bool(wait),
            )
            status = result["status"]
            if status == "granted":
                head = (
                    f"✓ Lease granted (claim_id={result['claim_id']}, ttl={result['ttl_seconds']:g}s): "
                    f"{', '.join(result['paths'])}. Selesai edit -> panggil release_claim."
                )
            elif status == "conflict":
                head = "KONFLIK: path dipegang agent lain. Lihat field conflicts (pemilik, sisa TTL) dan options."
            else:
                head = (
                    f"Antri (request_id={result['request_id']}, posisi {result['waiters_ahead'] + 1}). "
                    "Akan granted otomatis saat lease bebas; cek lagi dengan mengulang claim."
                )
            return ToolResult(output=f"{head}\n{_dump(result)}")
        except Exception as e:
            return ToolResult(error=str(e), ok=False)


class ReleaseClaimTool(Tool):
    name = "release_claim"
    description = (
        "Release lease claim milik agent (eksplisit, idempotent). Tanpa paths: seluruh claim agent "
        "dilepas dan semua request antrian miliknya dibatalkan. Respons berisi lease yang dilepas, "
        "antrian yang dibatalkan, dan waiter mana yang otomatis dipromosikan."
    )
    parameters = {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Path spesifik yang di-release (opsional; tanpa ini semua claim agent dilepas).",
            },
            "agent_id": {"type": "string", "description": "Identitas agent; default env AUTOKEREN_AGENT_ID atau 'main'."},
            "request_id": {"type": "string", "description": "ID request antrian (w-...) yang ingin dibatalkan."},
            "cancel_waiters": {
                "type": "boolean",
                "description": "Sekaligus batalkan semua request antrian claim milik agent.",
            },
        },
    }

    def __init__(self, project_root: Path | str) -> None:
        self.store = CoordStore(project_root)

    def run(
        self,
        paths: Any = None,
        agent_id: str | None = None,
        request_id: str | None = None,
        cancel_waiters: bool = False,
        **_: Any,
    ) -> ToolResult:
        try:
            result = self.store.release(
                agent_id=str(agent_id).strip() if agent_id else _default_agent_id(),
                paths=_as_path_list(paths) if paths else None,
                request_id=request_id,
                cancel_waiters=bool(cancel_waiters),
            )
            head = (
                f"✓ Released: {result['released'] or '-'} | antrian dibatalkan: {result['cancelled'] or '-'} | "
                f"dipromosikan: {[p['agent_id'] for p in result['promoted']] or '-'}"
            )
            return ToolResult(output=f"{head}\n{_dump(result)}")
        except Exception as e:
            return ToolResult(error=str(e), ok=False)


class MergeQueueTool(Tool):
    name = "merge_queue"
    description = (
        "Merge queue per-branch untuk changeset antar-agent. enqueue: masukkan change (set-of-paths) "
        "ke antrian FIFO; status change diuji overlap path dengan change di depannya -> pass (boleh "
        "merge), queued (menunggu giliran, aman), conflict (overlap, terblokir). status: lihat antrian. "
        "dequeue: keluarkan change yang sudah selesai merge/withdraw; antrian di belakangnya di-render ulang."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["enqueue", "status", "dequeue"],
                "description": "Aksi pada merge queue branch.",
            },
            "branch": {"type": "string", "description": "Nama branch queue (mis. main)."},
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Set-of-paths change; wajib untuk enqueue.",
            },
            "change_id": {"type": "string", "description": "ID change; wajib untuk dequeue, opsional untuk enqueue."},
            "agent_id": {"type": "string", "description": "Identitas agent; default env AUTOKEREN_AGENT_ID atau 'main'."},
        },
        "required": ["action", "branch"],
    }

    def __init__(self, project_root: Path | str) -> None:
        self.store = CoordStore(project_root)

    def run(
        self,
        action: str,
        branch: str,
        paths: Any = None,
        change_id: str | None = None,
        agent_id: str | None = None,
        **_: Any,
    ) -> ToolResult:
        agent = str(agent_id).strip() if agent_id else _default_agent_id()
        try:
            if action == "enqueue":
                if not paths:
                    return ToolResult(error="Parameter 'paths' wajib diisi untuk aksi 'enqueue'.", ok=False)
                result = self.store.queue_enqueue(
                    branch=branch,
                    paths=_as_path_list(paths),
                    agent_id=agent,
                    change_id=change_id,
                )
                head = f"✓ Change {result['change_id']} masuk queue '{branch}' posisi {result['position']}/{result['queue_length']} -> status: {result['status'].upper()}"
                if result["blocked_by"]:
                    head += f" (blocked_by: {result['blocked_by']})"
                return ToolResult(output=f"{head}\n{_dump(result)}")
            if action == "status":
                result = self.store.queue_status(branch=branch, change_id=change_id)
                lines = [
                    f"posisi {e['position']}: {e['change_id']} oleh {e['agent_id']} -> {e['status'].upper()} blocked_by={e['blocked_by']}"
                    for e in result[branch]
                ]
                return ToolResult(output=f"Queue '{branch}' ({len(result[branch])} change):\n" + "\n".join(lines))
            if action == "dequeue":
                if not change_id:
                    return ToolResult(error="Parameter 'change_id' wajib diisi untuk aksi 'dequeue'.", ok=False)
                result = self.store.queue_dequeue(branch=branch, change_id=change_id)
                head = f"✓ Change {result['removed']['change_id']} keluar dari queue '{branch}' (sisa {result['queue_length']})."
                return ToolResult(output=f"{head}\n{_dump(result)}")
            return ToolResult(error=f"Aksi tidak dikenal: {action} (pilih enqueue/status/dequeue).", ok=False)
        except Exception as e:
            return ToolResult(error=str(e), ok=False)
