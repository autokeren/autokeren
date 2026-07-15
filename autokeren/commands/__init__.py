"""Slash command registry and dispatch for autokeren."""
from __future__ import annotations

from typing import Any, Callable

from autokeren.commands.sync import handle_slash_command_sync

__all__ = ["handle_slash_command_sync", "dispatch_slash"]

_dispatch_table: dict[str, Callable[..., str | None]] = {}


def register(cmd: str) -> Callable:
    """Decorator to register a slash command handler."""

    def wrapper(fn: Callable[..., str | None]) -> Callable[..., str | None]:
        _dispatch_table[cmd] = fn
        return fn

    return wrapper


def dispatch_slash(
    cmd_line: str,
    agent: Any,
    cfg: Any,
    mcp_clients: list[Any],
    set_allow_all_fn: Any,
    console: Any,
) -> str | None:
    """Dispatch a slash command line. Returns output text or None if not handled."""
    parts = cmd_line.strip().split(" ", 1)
    cmd = parts[0].lower()

    # Try sync commands first (config, mcp, approval, etc.)
    sync_res = handle_slash_command_sync(cmd_line, agent, cfg, mcp_clients, set_allow_all_fn)
    if sync_res is not None:
        return sync_res

    # Try registered commands
    handler = _dispatch_table.get(cmd)
    if handler:
        return handler(cmd_line=cmd_line, agent=agent, cfg=cfg, console=console)

    return None
# ak:4917cb320deaf8e9
