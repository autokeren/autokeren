"""Checkpoint storage — file-based, rotation, session-scoped."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _checkpoint_dir(project_root: Path, session_id: str) -> Path:
    d = project_root / ".ak-checkpoints" / f"session-{session_id}"
    try:
        d.mkdir(parents=True, exist_ok=True)
        test_file = d / ".test_write"
        test_file.touch()
        test_file.unlink()
        return d
    except (OSError, PermissionError):
        from autokeren.memory import _config_base, _project_slug
        project_dir = _config_base() / "projects" / _project_slug(str(project_root))
        d_fallback = project_dir / ".ak-checkpoints" / f"session-{session_id}"
        d_fallback.mkdir(parents=True, exist_ok=True)
        return d_fallback


class CheckpointStorage:
    """File-based storage untuk checkpoints."""

    def __init__(self, project_root: Path, session_id: str, max_checkpoints: int = 50) -> None:
        self.project_root = project_root
        self.session_id = session_id
        self.max_checkpoints = max_checkpoints
        self.dir = _checkpoint_dir(project_root, session_id)

    def save(self, checkpoint_id: int, data: dict[str, Any]) -> Path:
        path = self.dir / f"{checkpoint_id:04d}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._rotate()
        return path

    def load(self, checkpoint_id: int) -> dict[str, Any] | None:
        path = self.dir / f"{checkpoint_id:04d}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def delete(self, checkpoint_id: int) -> bool:
        path = self.dir / f"{checkpoint_id:04d}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_ids(self) -> list[int]:
        ids: list[int] = []
        for f in sorted(self.dir.glob("*.json")):
            if f.stem == "meta":
                continue
            try:
                ids.append(int(f.stem))
            except ValueError:
                continue
        return ids

    def save_meta(self, meta: dict[str, Any]) -> None:
        path = self.dir / "meta.json"
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_meta(self) -> dict[str, Any] | None:
        path = self.dir / "meta.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _rotate(self) -> None:
        """Hapus checkpoint tertua kalau melebihi max_checkpoints."""
        ids = self.list_ids()
        while len(ids) > self.max_checkpoints:
            oldest = ids.pop(0)
            self.delete(oldest)

    def clear(self) -> None:
        """Hapus semua checkpoint."""
        for f in self.dir.glob("*.json"):
            f.unlink()

    def count(self) -> int:
        return len(self.list_ids())

    def latest_id(self) -> int | None:
        ids = self.list_ids()
        return ids[-1] if ids else None
