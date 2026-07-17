"""Ghost Agent Manager — spawn background agents via tmux."""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class GhostAgentInfo:
    id: int
    task: str
    status: str = "pending"
    pid: int | None = None
    started_at: float = 0.0
    log_file: str = ""
    role: str = ""
    model_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task": self.task[:80],
            "status": self.status,
            "runtime": round(self.runtime, 1),
            "role": self.role,
            "model_id": self.model_id,
        }

    @property
    def runtime(self) -> float:
        if self.is_running:
            return time.time() - self.started_at
        return 0.0

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def meta_file(self) -> Path:
        return Path(self.log_file).parent / f".ak-ghost-{self.id}.json"


class GhostManager:
    """Manage background ghost agents via tmux."""

    def __init__(self, project_root: str, max_agents: int = 3, prefix: str = "ak-ghost") -> None:
        self.project_root = project_root
        self.max_agents = max_agents
        self.prefix = prefix
        self._agents: dict[int, GhostAgentInfo] = {}
        self._next_id = 1
        self._load_existing()

    def _load_existing(self) -> None:
        """Load metadata dari file .ak-ghost-*.json untuk survive restart."""
        root = Path(self.project_root)
        for meta_path in root.glob(".ak-ghost-*.json"):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                agent_id = data.get("id", 0)
                if not agent_id:
                    continue
                info = GhostAgentInfo(
                    id=agent_id,
                    task=data.get("task", ""),
                    status="running",
                    started_at=time.mktime(time.strptime(
                        data.get("started_at", "2000-01-01T00:00:00Z").replace("Z", "+0000"),
                    )) if data.get("started_at") else 0.0,
                    log_file=str(root / f".ak-ghost-{agent_id}.log"),
                    role=data.get("role", ""),
                    model_id=data.get("model_id", ""),
                )
                session_name = f"{self.prefix}-{agent_id}"
                check = subprocess.run(
                    ["tmux", "has-session", "-t", session_name], capture_output=True,
                )
                if check.returncode != 0:
                    info.status = "completed"
                self._agents[agent_id] = info
                if agent_id >= self._next_id:
                    self._next_id = agent_id + 1
            except Exception:
                pass

    def spawn(self, task: str, role: str = "", model_id: str = "") -> GhostAgentInfo:
        if self.active_count >= self.max_agents:
            raise RuntimeError(f"Maksimal {self.max_agents} ghost agent.")

        agent_id = self._next_id
        while True:
            session_name = f"{self.prefix}-{agent_id}"
            check = subprocess.run(
                ["tmux", "has-session", "-t", session_name], capture_output=True,
            )
            if check.returncode != 0:
                break
            agent_id += 1

        self._next_id = agent_id + 1
        import shlex

        log_file = str(Path(self.project_root) / f".ak-ghost-{agent_id}.log")
        meta_file = Path(self.project_root) / f".ak-ghost-{agent_id}.json"
        info = GhostAgentInfo(
            id=agent_id, task=task, status="running",
            started_at=time.time(), log_file=log_file,
            role=role, model_id=model_id,
        )
        try:
            meta_data = {
                "id": agent_id,
                "task": task,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(info.started_at)),
                "role": role,
                "model_id": model_id,
            }
            meta_file.write_text(json.dumps(meta_data), encoding="utf-8")

            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session_name, "-c", self.project_root],
                check=True, capture_output=True,
            )

            args = ["autokeren", "--non-interactive"]
            if role:
                args.extend(["--role", role])
            if model_id:
                args.extend(["--model", model_id])
            args.extend(["--task", task])

            cmd = " ".join(shlex.quote(a) for a in args) + f" 2>&1 | tee {shlex.quote(log_file)}; exit"
            subprocess.run(
                ["tmux", "send-keys", "-t", session_name, cmd, "Enter"],
                check=True, capture_output=True,
            )
        except Exception as e:
            info.status = "failed"
            self._agents[agent_id] = info
            raise RuntimeError(f"Failed to spawn: {e}")
        self._agents[agent_id] = info
        return info

    def check_status(self, agent_id: int) -> str:
        info = self._agents.get(agent_id)
        if not info:
            return "unknown"
        session_name = f"{self.prefix}-{agent_id}"
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name], capture_output=True,
        )
        if result.returncode != 0:
            info.status = "completed"
        return info.status

    def kill(self, agent_id: int) -> bool:
        info = self._agents.get(agent_id)
        if not info:
            return False
        subprocess.run(
            ["tmux", "kill-session", "-t", f"{self.prefix}-{agent_id}"],
            capture_output=True,
        )
        info.status = "killed"
        meta_file = Path(self.project_root) / f".ak-ghost-{agent_id}.json"
        if meta_file.exists():
            try:
                meta_file.unlink()
            except Exception:
                pass
        return True

    def list_agents(self) -> list[GhostAgentInfo]:
        return list(self._agents.values())

    def get_output(self, agent_id: int, max_chars: int = 50000) -> str:
        info = self._agents.get(agent_id)
        if not info or not info.log_file:
            return ""
        try:
            content = Path(info.log_file).read_text(encoding="utf-8", errors="replace")
            if len(content) > max_chars:
                return content[-max_chars:]
            return content
        except Exception:
            return ""

    @property
    def active_count(self) -> int:
        return sum(1 for a in self._agents.values() if a.is_running)
# ak:9cb6c4c33f423258
