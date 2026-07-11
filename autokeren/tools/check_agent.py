"""autokeren.tools.check_agent — Tool untuk memantau status sub-agent background."""
from __future__ import annotations

from autokeren.tools.base import Tool, ToolResult


class CheckAgentTool(Tool):
    """Tool untuk memantau status sub-agent background (ghost agent)."""

    name = "check_agent"
    description = (
        "Periksa status dan log output dari sub-agent background (ghost agent) yang berjalan di sesi tmux."
    )
    parameters = {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "integer",
                "description": "ID numerik dari sub-agent (misal: 1, 2).",
            },
        },
        "required": ["agent_id"],
    }
    requires_permission = False

    def __init__(self, cfg: object, project_root: str, memory: object) -> None:
        self._cfg = cfg
        self._project_root = project_root
        self._memory = memory

    def permission_desc(self, **kwargs: object) -> str:
        agent_id = kwargs.get("agent_id", "?")
        return f"Memeriksa status background agent #{agent_id}..."

    def run(self, agent_id: int, **_: object) -> ToolResult:
        from autokeren.ghost.manager import GhostManager
        try:
            mgr = GhostManager(self._project_root)
            agents = {a.id: a for a in mgr.list_agents()}
            if agent_id not in agents:
                return ToolResult(
                    output=f"Agent #{agent_id} tidak ditemukan atau belum berjalan di background."
                )
            
            info = agents[agent_id]
            status = mgr.check_status(agent_id)
            output = mgr.get_output(agent_id)
            
            lines = output.splitlines()
            if len(lines) > 50:
                truncated_output = "\n".join(lines[-50:])
                log_info = f"\n[Output log 50 baris terakhir dari total {len(lines)} baris]:\n...\n{truncated_output}"
            else:
                log_info = f"\n[Output log lengkap]:\n{output}" if output else "\n[Log kosong / belum ada output]"
                
            return ToolResult(
                output=(
                    f"🤖 STATUS AGENT #{agent_id}:\n"
                    f"Task: {info.task}\n"
                    f"Status: {status.upper()}\n"
                    f"Runtime: {info.runtime:.1f} detik\n"
                    f"{log_info}"
                )
            )
        except Exception as e:
            return ToolResult(
                output=f"Error saat memeriksa agent #{agent_id}: {e}",
                error=str(e),
            )
