"""Interactive keyboard selector — arrow up/down, number keys, enter."""
from __future__ import annotations

import sys
from typing import Any


def select_option(
    options: list[dict[str, Any]],
    title: str = "Pilih",
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

    import tty
    import termios

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    selected = 0
    n = len(options)

    def render_lines() -> list[str]:
        lines = [f"\n  {title}\n"]
        for i, opt in enumerate(options):
            name = opt.get("name", opt.get("id", str(opt)))
            desc = opt.get("desc", "")
            tier = opt.get("tier", "")
            icon = opt.get("icon", "")
            marker = "▶" if i == selected else " "
            tier_str = f" [{tier}]" if tier else ""
            desc_str = f"  — {desc}" if desc else ""
            if i == selected:
                lines.append(f"  {marker} \033[1;36m{icon} {name}\033[0m\033[2m{tier_str}{desc_str}\033[0m")
            else:
                lines.append(f"  {marker} \033[37m{icon} {name}\033[0m\033[2m{tier_str}{desc_str}\033[0m")
        lines.append("")
        lines.append("  \033[2m↑↓ navigasi  •  1-9 pilih  •  Enter konfirmasi  •  q batal\033[0m")
        return lines

    def draw() -> None:
        # Clear previous draw: move cursor up n+4 lines and clear each
        clear_count = n + 4
        sys.stdout.write(f"\033[{clear_count}A")
        for _ in range(clear_count):
            sys.stdout.write("\033[K\033[B")
        sys.stdout.write(f"\033[{clear_count}A")
        # Draw new
        for line in render_lines():
            sys.stdout.write(line + "\n")
        sys.stdout.flush()

    try:
        tty.setraw(fd)
        # Initial draw
        for line in render_lines():
            sys.stdout.write(line + "\n")
        sys.stdout.flush()

        while True:
            ch = sys.stdin.read(1)
            if ch == "\r" or ch == "\n":
                break
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":
                        selected = (selected - 1) % n
                        draw()
                    elif ch3 == "B":
                        selected = (selected + 1) % n
                        draw()
                else:
                    return None
            elif ch == "q":
                return None
            elif ch >= "1" and ch <= "9":
                idx = int(ch) - 1
                if idx < n:
                    selected = idx
                    draw()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return selected
