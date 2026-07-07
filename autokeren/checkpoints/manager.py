"""Checkpoint manager — create, load, rewind tool call checkpoints."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autokeren.checkpoints.storage import CheckpointStorage


@dataclass
class FileChange:
    path: str
    action: str  # "create", "modify", "delete"
    before: str | None = None
    after: str | None = None


@dataclass
class Checkpoint:
    id: int
    timestamp: float
    tool_name: str
    tool_args: dict[str, Any]
    tool_result: dict[str, Any]
    tool_ok: bool
    file_changes: list[FileChange] = field(default_factory=list)


class CheckpointManager:
    """Manage checkpoints untuk Time-Travel /rewind."""

    def __init__(
        self,
        project_root: Path,
        session_id: str = "default",
        max_checkpoints: int = 50,
        auto_checkpoint: bool = True,
    ) -> None:
        self.project_root = project_root
        self.storage = CheckpointStorage(project_root, session_id, max_checkpoints)
        self.auto_checkpoint = auto_checkpoint
        self._next_id = 1
        self._init_next_id()

    def _init_next_id(self) -> None:
        ids = self.storage.list_ids()
        self._next_id = (max(ids) + 1) if ids else 1

    def _snapshot_file(self, path: str) -> str | None:
        p = self.project_root / path
        if not p.exists() or not p.is_file():
            return None
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def _detect_changes(
        self, tool_name: str, tool_args: dict[str, Any], before_snapshot: dict[str, str | None]
    ) -> list[FileChange]:
        changes: list[FileChange] = []
        if tool_name not in ("write_file", "patch_file"):
            return changes
        path = tool_args.get("path", "")
        if not path:
            return changes
        before = before_snapshot.get(path)
        after = self._snapshot_file(path)
        if before is None and after is not None:
            changes.append(FileChange(path=path, action="create", before=None, after=after))
        elif before is not None and after is not None:
            if before != after:
                changes.append(FileChange(path=path, action="modify", before=before, after=after))
        elif before is not None and after is None:
            changes.append(FileChange(path=path, action="delete", before=before, after=None))
        return changes

    def save(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: dict[str, Any],
        tool_ok: bool,
        before_snapshot: dict[str, str | None] | None = None,
    ) -> Checkpoint:
        if before_snapshot is None:
            before_snapshot = {}
        changes = self._detect_changes(tool_name, tool_args, before_snapshot)
        cp_id = self._next_id
        self._next_id += 1
        now = time.time()
        data = {
            "id": cp_id,
            "timestamp": now,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result,
            "tool_ok": tool_ok,
            "file_changes": [
                {"path": c.path, "action": c.action, "before": c.before, "after": c.after}
                for c in changes
            ],
        }
        self.storage.save(cp_id, data)
        self.storage.save_meta({"next_id": self._next_id})
        ts: float = now
        return Checkpoint(
            id=cp_id,
            timestamp=ts,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            tool_ok=tool_ok,
            file_changes=changes,
        )

    def rewind(self, steps: int = 1) -> list[Checkpoint]:
        if steps < 1:
            steps = 1
        ids = self.storage.list_ids()
        if not ids:
            return []
        to_undo = ids[-steps:] if steps <= len(ids) else ids[:]
        undone: list[Checkpoint] = []
        for cp_id in reversed(to_undo):
            data = self.storage.load(cp_id)
            if data is None:
                continue
            changes = [
                FileChange(
                    path=c["path"],
                    action=c["action"],
                    before=c.get("before"),
                    after=c.get("after"),
                )
                for c in data.get("file_changes", [])
            ]
            cp = Checkpoint(
                id=cp_id,
                timestamp=data["timestamp"],
                tool_name=data["tool_name"],
                tool_args=data.get("tool_args", {}),
                tool_result=data.get("tool_result", {}),
                tool_ok=data.get("tool_ok", True),
                file_changes=changes,
            )
            self._revert_changes(changes)
            self.storage.delete(cp_id)
            undone.append(cp)
        if undone:
            self._next_id = undone[-1].id
            self.storage.save_meta({"next_id": self._next_id})
        return undone

    def _revert_changes(self, changes: list[FileChange]) -> None:
        for change in reversed(changes):
            p = self.project_root / change.path
            if change.action == "create":
                if p.exists():
                    p.unlink()
            elif change.action == "modify":
                if change.before is not None:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(change.before, encoding="utf-8")
            elif change.action == "delete":
                if change.before is not None:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(change.before, encoding="utf-8")

    def list_checkpoints(self) -> list[dict[str, Any]]:
        ids = self.storage.list_ids()
        result = []
        for cp_id in ids:
            data = self.storage.load(cp_id)
            if data is None:
                continue
            result.append({
                "id": cp_id,
                "timestamp": data["timestamp"],
                "tool": data["tool_name"],
                "args": data.get("tool_args", {}),
                "ok": data.get("tool_ok", True),
                "changes": len(data.get("file_changes", [])),
            })
        return result

    def count(self) -> int:
        return self.storage.count()

    def clear(self) -> None:
        self.storage.clear()
        self._next_id = 1
        self.storage.save_meta({"next_id": 1})

    def snapshot_files(self, paths: list[str]) -> dict[str, str | None]:
        return {p: self._snapshot_file(p) for p in paths}
