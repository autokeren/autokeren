"""Coordination tools — claim/lease, release, and merge queue for agent-to-agent coordination."""
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
        "Claim/lease files BEFORE editing so you don't collide with another agent working on the "
        "same file. Multi-path claims are atomic. Leases carry a TTL and auto-expire; call "
        "release_claim when you finish editing. If a path is held by another agent, the response "
        "contains the owner, remaining TTL, and the wait option (join the FIFO queue)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File paths relative to the project root to edit (all claimed atomically).",
            },
            "agent_id": {
                "type": "string",
                "description": "Agent identity; defaults to env AUTOKEREN_AGENT_ID or 'main'.",
            },
            "ttl_seconds": {
                "type": "number",
                "description": "Lease TTL in seconds; the lease auto-expires after the TTL (default 300).",
            },
            "branch": {"type": "string", "description": "Branch context of the claim (optional)."},
            "wait": {
                "type": "boolean",
                "description": "If true and a path conflicts, the request joins the FIFO queue and is "
                "auto-promoted once the lease frees up.",
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
                    f"{', '.join(result['paths'])}. Done editing -> call release_claim."
                )
            elif status == "conflict":
                head = "CONFLICT: path is held by another agent. See the conflicts field (owner, remaining TTL) and options."
            else:
                head = (
                    f"Queued (request_id={result['request_id']}, position {result['waiters_ahead'] + 1}). "
                    "Granted automatically once the lease frees up; check again by re-claiming."
                )
            return ToolResult(output=f"{head}\n{_dump(result)}")
        except Exception as e:
            return ToolResult(error=str(e), ok=False)


class ReleaseClaimTool(Tool):
    name = "release_claim"
    description = (
        "Explicitly release an agent's lease claims (idempotent). Without paths: all of the agent's "
        "claims are released and all of its queued requests are cancelled. The response lists the "
        "released leases, the cancelled queue entries, and which waiters were automatically promoted."
    )
    parameters = {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific paths to release (optional; without this, all of the agent's claims are released).",
            },
            "agent_id": {
                "type": "string",
                "description": "Agent identity; defaults to env AUTOKEREN_AGENT_ID or 'main'.",
            },
            "request_id": {"type": "string", "description": "ID of the queued request (w-...) to cancel."},
            "cancel_waiters": {
                "type": "boolean",
                "description": "Also cancel all of the agent's queued claim requests.",
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
                f"✓ Released: {result['released'] or '-'} | queue cancelled: {result['cancelled'] or '-'} | "
                f"promoted: {[p['agent_id'] for p in result['promoted']] or '-'}"
            )
            return ToolResult(output=f"{head}\n{_dump(result)}")
        except Exception as e:
            return ToolResult(error=str(e), ok=False)


class MergeQueueTool(Tool):
    name = "merge_queue"
    description = (
        "Per-branch merge queue for agent changesets. enqueue: put a change (set-of-paths) into the "
        "FIFO queue; the change's status is tested for path overlap against the changes ahead of it -> "
        "pass (cleared to merge), queued (waiting its turn, safe), conflict (overlap, blocked). status: "
        "view the queue. dequeue: remove a change that finished merging or was withdrawn; the changes "
        "behind it are re-evaluated."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["enqueue", "status", "dequeue"],
                "description": "Action on the branch's merge queue.",
            },
            "branch": {"type": "string", "description": "Branch queue name (e.g. main)."},
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The change's set-of-paths; required for enqueue.",
            },
            "change_id": {
                "type": "string",
                "description": "Change ID; required for dequeue, optional for enqueue.",
            },
            "agent_id": {
                "type": "string",
                "description": "Agent identity; defaults to env AUTOKEREN_AGENT_ID or 'main'.",
            },
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
                    return ToolResult(error="Parameter 'paths' is required for action 'enqueue'.", ok=False)
                result = self.store.queue_enqueue(
                    branch=branch,
                    paths=_as_path_list(paths),
                    agent_id=agent,
                    change_id=change_id,
                )
                head = (
                    f"✓ Change {result['change_id']} enqueued in '{branch}' at position "
                    f"{result['position']}/{result['queue_length']} -> status: {result['status'].upper()}"
                )
                if result["blocked_by"]:
                    head += f" (blocked_by: {result['blocked_by']})"
                return ToolResult(output=f"{head}\n{_dump(result)}")
            if action == "status":
                result = self.store.queue_status(branch=branch, change_id=change_id)
                lines = [
                    f"position {e['position']}: {e['change_id']} by {e['agent_id']} -> "
                    f"{e['status'].upper()} blocked_by={e['blocked_by']}"
                    for e in result[branch]
                ]
                return ToolResult(output=f"Queue '{branch}' ({len(result[branch])} changes):\n" + "\n".join(lines))
            if action == "dequeue":
                if not change_id:
                    return ToolResult(error="Parameter 'change_id' is required for action 'dequeue'.", ok=False)
                result = self.store.queue_dequeue(branch=branch, change_id=change_id)
                head = (
                    f"✓ Change {result['removed']['change_id']} dequeued from '{branch}' "
                    f"({result['queue_length']} remaining)."
                )
                return ToolResult(output=f"{head}\n{_dump(result)}")
            return ToolResult(error=f"Unknown action: {action} (choose enqueue/status/dequeue).", ok=False)
        except Exception as e:
            return ToolResult(error=str(e), ok=False)
