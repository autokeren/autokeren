"""Simple model selector — nomor + enter."""
from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from autokeren.ui import AK_THEME


def select_option(
    options: list[dict[str, Any]],
    title: str = "Pilih",
    console: Console | None = None,
) -> int | None:
    """Tampilkan list, user ketik nomor. Return index atau None kalau batal."""
    if not options:
        return None
    if len(options) == 1:
        return 0

    console = console or Console(theme=AK_THEME)

    lines = Text()
    lines.append(f"{title}\n\n", style="bold")
    for i, opt in enumerate(options):
        name = opt.get("name", opt.get("id", str(opt)))
        desc = opt.get("desc", "")
        tier = opt.get("tier", "")
        icon = opt.get("icon", "")
        tier_str = f" [{tier}]" if tier else ""
        desc_str = f"  {desc}" if desc else ""
        lines.append(f"  {i + 1}. ", style="bold cyan")
        lines.append(f"{icon} {name}", style="white")
        lines.append(f"{tier_str}{desc_str}\n", style="dim")
    lines.append("\n  Ketik nomor (atau q untuk batal): ", style="dim")

    console.print(Panel(lines, border_style="blue"))

    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if choice.lower() == "q" or not choice:
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return idx
        console.print(f"[red]Nomor {choice} di luar range (1-{len(options)})[/red]")
        return None
    except ValueError:
        console.print(f"[red]Input tidak valid: {choice}[/red]")
        return None
