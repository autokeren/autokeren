"""Interactive keyboard selector — arrow up/down, number keys, enter."""
from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


def select_option(
    options: list[dict[str, Any]],
    title: str = "Pilih",
    console: Console | None = None,
) -> int | None:
    """Interactive selector. Return index atau None kalau cancel.

    Navigation:
      ↑/↓     : pindah selection
      1-9     : pilih langsung by number
      Enter   : konfirmasi
      q/Esc   : cancel
    """
    if not options:
        return None
    if len(options) == 1:
        return 0

    console = console or Console()
    selected = 0

    import tty
    import termios

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    def render() -> Panel:
        lines = Text()
        lines.append(f"{title}\n\n", style="bold")
        for i, opt in enumerate(options):
            marker = "▶" if i == selected else " "
            name = opt.get("name", opt.get("id", str(opt)))
            desc = opt.get("desc", "")
            tier = opt.get("tier", "")
            icon = opt.get("icon", "")

            if i == selected:
                lines.append(f"  {marker} ", style="bold cyan")
                lines.append(f"{icon} {name}", style="bold cyan")
                if tier:
                    lines.append(f" [{tier}]", style="dim")
                if desc:
                    lines.append(f"  {desc}", style="dim")
            else:
                lines.append(f"  {marker} ", style="dim")
                lines.append(f"{icon} {name}", style="white")
                if tier:
                    lines.append(f" [{tier}]", style="dim")
                if desc:
                    lines.append(f"  {desc}", style="dim")
            lines.append("\n")
        lines.append("\n", style="")
        lines.append("  ↑↓ navigasi  •  1-9 pilih cepat  •  Enter konfirmasi  •  q batal", style="dim")
        return Panel(lines, border_style="blue")

    try:
        tty.setraw(fd)
        with Live(render(), console=console, refresh_per_second=30, transient=True) as live:
            while True:
                ch = sys.stdin.read(1)
                if ch == "\r" or ch == "\n":
                    break
                if ch == "\x1b":
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        if ch3 == "A":
                            selected = (selected - 1) % len(options)
                        elif ch3 == "B":
                            selected = (selected + 1) % len(options)
                    else:
                        return None
                elif ch == "q":
                    return None
                elif ch >= "1" and ch <= "9":
                    idx = int(ch) - 1
                    if idx < len(options):
                        selected = idx
                live.update(render())
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return selected
