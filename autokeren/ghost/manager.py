"""Ghost Agent Manager — spawn background agents via tmux."""
from __future__ import annotations

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task": self.task[:80],
            "status": self.status,
            "runtime": round(self.runtime, 1),
        }

    @property
    def runtime(self) -> float:
        if self.is_running:
            return time.time() - self.started_at
        return 0.0

    @property
    def is_running(self) -> bool:
        return self.status == "running"


class GhostManager:
    """Manage background ghost agents via tmux."""

    def __init__(self, project_root: str, max_agents: int = 3, prefix: str = "ak-ghost") -> None:
        self.project_root = project_root
        self.max_agents = max_agents
        self.prefix = prefix
        self._agents: dict[int, GhostAgentInfo] = {}
        self._next_id = 1

    def spawn(self, task: str) -> GhostAgentInfo:
        if len(self._agents) >= self.max_agents:
            raise RuntimeError(f"Maksimal {self.max_agents} ghost agent.")
        agent_id = self._next_id
        self._next_id += 1
        session_name = f"{self.prefix}-{agent_id}"
        log_file = str(Path(self.project_root) / f".ak-ghost-{agent_id}.log")
        info = GhostAgentInfo(
            id=agent_id, task=task, status="running",
            started_at=time.time(), log_file=log_file,
        )
        try:
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session_name, "-c", self.project_root],
                check=True, capture_output=True,
            )
            cmd = f'autokeren --non-interactive --task "{task}" 2>&1 | tee {log_file}'
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
        return True

    def list_agents(self) -> list[GhostAgentInfo]:
        return list(self._agents.values())

    def get_output(self, agent_id: int) -> str:
        info = self._agents.get(agent_id)
        if not info or not info.log_file:
            return ""
        try:
            return Path(info.log_file).read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    @property
    def active_count(self) -> int:
        return sum(1 for a in self._agents.values() if a.is_running)
