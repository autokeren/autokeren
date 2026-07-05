"""Mermaid diagram renderer — inline image di terminal + fallback.

1. Render PNG via mermaid.ink
2. Tampilkan inline pakai iTerm2/kitty/wezterm protocol (gambar asli di terminal)
3. Fallback: chafa (ANSI art) kalau ada
4. Fallback: text arrows kalau semua gagal
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from rich.console import Console

_PARTICIPANT_COLORS = ["cyan", "green", "yellow", "magenta", "blue", "red", "bright_cyan", "bright_green"]


def extract_mermaid_blocks(text: str) -> list[str]:
    """Extract all ```mermaid code blocks from text."""
    blocks: list[str] = []
    for match in re.finditer(r"```mermaid\s*\n(.*?)```", text, re.DOTALL):
        code = match.group(1).strip()
        if code:
            blocks.append(code)
    return blocks


def extract_and_render(text: str, console: Console) -> None:
    """Find all mermaid blocks, render as image, fallback to text."""
    blocks = extract_mermaid_blocks(text)
    if not blocks:
        return
    console.print()
    for i, block in enumerate(blocks):
        console.print(f"  [bold blue]🖼️ Diagram {i + 1}[/bold blue]")
        if not _try_render_image(block, console):
            render_mermaid_text(block, console)
        console.print()


# ------------------------------------------------------------------ #
# Image rendering
# ------------------------------------------------------------------ #


def _can_render_image() -> bool:
    """Cek apakah terminal support inline image ATAU chafa tersedia."""
    return bool(_detect_terminal()) or bool(shutil.which("chafa"))


def _try_render_image(code: str, console: Console) -> bool:
    """Render mermaid ke PNG, tampilkan inline di terminal. Return False kalau gagal."""
    if not _can_render_image():
        return False

    try:
        encoded = base64.urlsafe_b64encode(code.encode("utf-8")).decode("ascii")
        url = f"https://mermaid.ink/img/{encoded}?type=png&bgColor=white"
        resp = httpx.get(url, timeout=15.0, follow_redirects=True)
        if resp.status_code != 200:
            return False

        png_data = resp.content

        if _try_inline_image(png_data):
            console.print("  [green]✓[/green] [dim]Diagram dirender inline[/dim]")
            return True

        if _try_chafa(png_data, console):
            return True

        _save_and_hint(png_data, console)
        return True

    except Exception as e:
        console.print(f"  [dim]⚠ Render gambar gagal ({type(e).__name__}), fallback ke text[/dim]")
        return False


def _detect_terminal() -> str:
    """Deteksi jenis terminal untuk inline image protocol."""
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program in ("iTerm.app", "WezTerm", "ghostty", "vscode"):
        return "iterm"
    if os.environ.get("ITERM_SESSION_ID"):
        return "iterm"
    if term_program == "kitty":
        return "kitty"
    if term_program == "BlackBox":
        return "iterm"
    return ""


def _try_inline_image(png_data: bytes) -> bool:
    """Kirim escape sequence untuk inline image (iTerm2/kitty protocol)."""
    term = _detect_terminal()
    if not term:
        return False

    b64 = base64.b64encode(png_data).decode("ascii")

    if term == "kitty":
        chunk_size = 4096
        sys.stdout.write("\033_Ga=T,f=100,t=f;")
        for i in range(0, len(b64), chunk_size):
            sys.stdout.write(b64[i : i + chunk_size])
            if i + chunk_size < len(b64):
                sys.stdout.write("\033\\\033_Gm=1;")
            else:
                sys.stdout.write("\033\\")
        sys.stdout.write("\n")
        sys.stdout.flush()
        return True

    sys.stdout.write(f"\033]1337;File=inline=1;width=auto:;{b64}\a\n")
    sys.stdout.flush()
    return True


def _try_chafa(png_data: bytes, console: Console) -> bool:
    """Fallback: render pakai chafa CLI kalau tersedia."""
    if not shutil.which("chafa"):
        return False
    try:
        result = subprocess.run(
            ["chafa", "--format=symbols", "--size=80x30", "--colors=240", "-"],
            input=png_data,
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout:
            console.print(result.stdout.decode("utf-8", errors="replace").rstrip())
            return True
    except Exception:
        pass
    return False


def _save_and_hint(png_data: bytes, console: Console) -> None:
    """Last resort: save PNG, kasih tau user path-nya."""
    tmp = Path(tempfile.gettempdir()) / "autokeren_mermaid"
    tmp.mkdir(exist_ok=True)
    img_path = tmp / f"diagram_{hash(png_data) & 0xFFFFFFFF:08x}.png"
    img_path.write_bytes(png_data)
    console.print("  [yellow]⚠ Terminal tidak support inline image[/yellow]")
    console.print(f"  [dim]   Saved: {img_path}[/dim]")
    console.print(f"  [dim]   Buka: xdg-open {img_path}[/dim]")


# ------------------------------------------------------------------ #
# Text fallback renderer
# ------------------------------------------------------------------ #


def render_mermaid_text(code: str, console: Console) -> None:
    """Parse and render mermaid. Coba visual dulu, fallback ke text arrows."""
    from autokeren.diagram import render_flowchart_visual, render_sequence_visual

    lines = code.strip().splitlines()
    if not lines:
        return

    first = lines[0].strip().lower()
    if first.startswith("sequencediagram"):
        if not render_sequence_visual(lines[1:], console):
            _render_sequence(lines[1:], console)
    elif first.startswith(("graph", "flowchart")):
        if not render_flowchart_visual(lines[1:], console):
            _render_flowchart(lines[1:], console)
    else:
        console.print(f"  [dim]Mermaid ({first or 'unknown'}):[/dim]")
        for line in lines[1:]:
            console.print(f"  [dim]{line}[/dim]")


def _render_sequence(lines: list[str], console: Console) -> None:
    participants: dict[str, str] = {}
    color_map: dict[str, str] = {}
    color_idx = 0
    indent_stack: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("autonumber", "sequenceDiagram")):
            continue

        indent = "    " * len(indent_stack)

        if line.startswith(("participant ", "actor ")):
            parts = line.split(None, 2)
            key = parts[1] if len(parts) > 1 else ""
            alias = key
            if len(parts) > 2 and parts[2].startswith("as "):
                alias = parts[2][3:].strip().strip('"')
            elif len(parts) > 2:
                alias = parts[2].strip().strip('"')
            participants[key] = alias
            if key not in color_map:
                color_map[key] = _PARTICIPANT_COLORS[color_idx % len(_PARTICIPANT_COLORS)]
                color_idx += 1
            continue

        if line.startswith("Note "):
            note_text = line.split(":", 1)[1].strip() if ":" in line else ""
            console.print(f"{indent}  [dim italic]📝 {note_text}[/dim italic]")
            continue

        if line.startswith("loop "):
            indent_stack.append("loop")
            console.print(f"{indent}  [bold yellow]↻ {line[5:].strip()}[/bold yellow]")
            continue

        if line.startswith("alt "):
            indent_stack.append("alt")
            console.print(f"{indent}  [bold magenta]◆ IF: {line[4:].strip()}[/bold magenta]")
            continue

        if line.startswith("else "):
            console.print(f"{indent}  [bold magenta]◆ ELSE: {line[5:].strip()}[/bold magenta]")
            continue

        if line.startswith("opt "):
            indent_stack.append("opt")
            console.print(f"{indent}  [bold blue]○ OPT: {line[4:].strip()}[/bold blue]")
            continue

        if line == "end" and indent_stack:
            indent_stack.pop()
            continue

        m = re.match(r"(\w+)\s*(-->>|-->|->>|->|-\)|--x|-x|>>>)\s*(\w+)(?::\s*(.*))?", line)
        if m:
            src_key, arrow, dst_key, msg = m.groups()
            src = participants.get(src_key, src_key)
            dst = participants.get(dst_key, dst_key)
            src_color = color_map.get(src_key, "white")
            dst_color = color_map.get(dst_key, "white")

            if "->>" in arrow or arrow == ">>>":
                ar = "──→"
            elif "-->" in arrow or "-->>" in arrow:
                ar = "···→"
            elif "-x" in arrow or "--x" in arrow:
                ar = "──✗"
            elif "-)" in arrow:
                ar = "···>"
            else:
                ar = "──→"

            msg_text = f": [dim]{msg}[/dim]" if msg else ""
            console.print(f"{indent}  [{src_color}]{src}[/{src_color}] {ar} [{dst_color}]{dst}[/{dst_color}]{msg_text}")
            continue


def _render_flowchart(lines: list[str], console: Console) -> None:
    node_labels: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []

    node_shape = r"(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\}|\(\(([^)]*)\)\))?"
    edge_re = re.compile(
        rf"(\w+){node_shape}\s*(-->|->|==>|-\.->|--x)\s*(?:\|([^|]*)\|\s*)?(\w+){node_shape}"
    )

    for line in lines:
        line = line.strip()
        if not line or line.startswith(("graph", "flowchart")):
            continue

        direction = line.split()[0] if line.split() else "TD"
        if direction in ("TD", "LR", "TB", "RL", "BT"):
            if len(line.split()) > 1:
                line = line.split(None, 1)[1]
            else:
                continue

        for m in edge_re.finditer(line):
            src_id = m.group(1)
            src_label = m.group(2) or m.group(3) or m.group(4) or m.group(5) or src_id
            edge_label = m.group(7) or ""
            dst_id = m.group(8)
            dst_label = m.group(9) or m.group(10) or m.group(11) or m.group(12) or dst_id

            if src_label != src_id or src_id not in node_labels:
                node_labels[src_id] = src_label
            if dst_label != dst_id or dst_id not in node_labels:
                node_labels[dst_id] = dst_label
            edges.append((src_id, dst_id, edge_label))

    if edges:
        for src, dst, label in edges:
            src_label = node_labels.get(src, src)
            dst_label = node_labels.get(dst, dst)
            label_text = f" [dim]({label})[/dim]" if label else ""
            console.print(f"  [cyan]{src_label}[/cyan] ──→ [green]{dst_label}[/green]{label_text}")
    else:
        for nid, label in node_labels.items():
            console.print(f"  [cyan]{nid}[/cyan] [dim]{label}[/dim]")
