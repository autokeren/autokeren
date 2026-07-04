"""Session manager — save/resume/list sessions per project."""
from __future__ import annotations

import json
from typing import Any

from autokeren.memory import _config_base, _project_slug
from autokeren.utils import now_iso, sanitize_filename


class SessionManager:
    """Kelola save/resume session per project.

    Sessions disimpan di ~/.config/autokeren/projects/<slug>/sessions/<id>-<name>.json
    Berisi: messages, usage stats, timestamp, name.
    """

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.sessions_dir = _config_base() / "projects" / _project_slug(project_root) / "sessions"

    def save(self, name: str, messages: list[dict[str, Any]], usage: dict[str, Any]) -> str:
        """Save session. Return session_id."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        session_id = now_iso().replace(":", "").replace("-", "")[:14]
        data = {
            "id": session_id,
            "name": name,
            "project": str(self.project_root),
            "timestamp": now_iso(),
            "messages": messages,
            "usage": usage,
        }
        safe_name = sanitize_filename(name)
        path = self.sessions_dir / f"{session_id}-{safe_name}.json"
        path.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")
        return session_id

    def load(self, identifier: str) -> dict[str, Any] | None:
        """Load session by id, name, atau partial filename. Return data atau None."""
        if not self.sessions_dir.exists():
            return None
        identifier_lower = identifier.lower()
        for p in sorted(self.sessions_dir.glob("*.json"), reverse=True):
            stem = p.stem.lower()
            data = json.loads(p.read_text(encoding="utf-8"))
            name = data.get("name", "").lower()
            sid = data.get("id", "").lower()
            if identifier_lower in stem or identifier_lower in name or identifier_lower == sid:
                return data
        return None

    def list(self) -> list[dict[str, Any]]:
        """List semua saved sessions."""
        if not self.sessions_dir.exists():
            return []
        sessions: list[dict[str, Any]] = []
        for p in sorted(self.sessions_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                sessions.append({
                    "id": data.get("id", ""),
                    "name": data.get("name", ""),
                    "timestamp": data.get("timestamp", ""),
                    "messages": len(data.get("messages", [])),
                    "file": p.name,
                })
            except Exception:
                continue
        return sessions

    def delete(self, identifier: str) -> bool:
        """Hapus session by identifier."""
        if not self.sessions_dir.exists():
            return False
        identifier_lower = identifier.lower()
        for p in self.sessions_dir.glob("*.json"):
            stem = p.stem.lower()
            data = json.loads(p.read_text(encoding="utf-8"))
            name = data.get("name", "").lower()
            sid = data.get("id", "").lower()
            if identifier_lower in stem or identifier_lower in name or identifier_lower == sid:
                p.unlink()
                return True
        return False
