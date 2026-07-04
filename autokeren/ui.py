"""Rich-based UI untuk autokeren CLI — banner, spinner, streaming, tool panel, permission, todo."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pyfiglet
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status
from rich.text import Text

if TYPE_CHECKING:
    from autokeren.models.base import ModelResponse
    from autokeren.tools.base import ToolResult

_RAINBOW = [
    "bold_red", "bold_yellow", "bold_green",
    "bold_cyan", "bold_blue", "bold_magenta",
]


class AgentUI:
    """UI layer untuk autokeren. Pure presentational, no business logic.

    Fitur:
    - Spinner "mikir…" saat model generate (sebelum chunk pertama)
    - Live streaming text saat token masuk real-time
    - Tool execution panel dengan nama + argumen ringkas
    - Permission confirmation untuk tool destruktif
    - Todo list display
    """

    def __init__(self, console: Console):
        self.console = console
        self._status: Status | None = None
        self._live: Live | None = None
        self._tool_label: str = ""
        self._stream_text: str = ""
        self._did_stream: bool = False
        self._allow_all: bool = False
        self._allowed_tools: set[str] = set()

    # ------------------------------------------------------------------ #
    # Banner startup
    # ------------------------------------------------------------------ #

    def show_banner(self, version: str = "0.1.0") -> None:
        """Tampilkan ASCII art banner warna-warni saat startup."""
        art = pyfiglet.figlet_format("AUTOKEREN", font="slant")
        lines = art.rstrip("\n").split("\n")
        colored = Text()
        for i, line in enumerate(lines):
            color = _RAINBOW[i % len(_RAINBOW)]
            colored.append(line + "\n", style=color)
        tagline = Text("  Cloudflare-first agentic coding CLI buat developer Indonesia\n", style="dim italic")
        ver = Text(f"  v{version}\n", style="bold yellow")
        self.console.print()
        self.console.print(Align.center(colored))
        self.console.print(Align.center(Group(tagline, ver)))
        self.console.print()

    # ------------------------------------------------------------------ #
    # Model thinking + streaming
    # ------------------------------------------------------------------ #

    def on_model_start(self) -> None:
        self._stop_all()
        self._stream_text = ""
        self._did_stream = False
        self._status = self.console.status("[dim]mikir…[/dim]", spinner="dots")
        self._status.start()

    def on_chunk(self, text: str) -> None:
        """Called untuk setiap text chunk dari streaming. Switch spinner → Live dengan Panel."""
        if self._status is not None:
            self._stop_status()
            self._live = Live(
                Panel("", title="autokeren"),
                console=self.console,
                refresh_per_second=12,
                vertical_overflow="visible",
            )
            self._live.start()
        self._did_stream = True
        self._stream_text += text
        if self._live is not None:
            self._live.update(Panel(self._stream_text, title="autokeren"))

    def on_model_end(self, resp: "ModelResponse") -> None:
        self._stop_all()
        self._stream_text = ""

    # ------------------------------------------------------------------ #
    # Tool execution — spinner while running, then result line
    # ------------------------------------------------------------------ #

    def on_tool_start(self, name: str, arguments: dict) -> None:
        self._stop_all()
        self._tool_label = f"[bold yellow]{name}[/bold yellow][dim]({_format_args(arguments)})[/dim]"
        self._status = self.console.status(
            f"  [bold cyan]→[/bold cyan] {self._tool_label}",
            spinner="dots",
        )
        self._status.start()

    def on_tool_end(self, name: str, result: "ToolResult") -> None:
        self._stop_all()
        label = self._tool_label or f"[bold yellow]{name}[/bold yellow]"
        if result.ok:
            summary = _summarize_output(result.output)
            tail = f"  [dim]{summary}[/dim]" if summary else ""
            self.console.print(f"  [green]✓[/green] {label}{tail}")
        else:
            err = result.error or "gagal"
            self.console.print(f"  [red]✗[/red] {label}  [red]{err}[/red]")

    # ------------------------------------------------------------------ #
    # Permission system
    # ------------------------------------------------------------------ #

    def confirm_permission(self, tool_name: str, description: str, arguments: dict) -> bool:
        """Tampilkan dialog konfirmasi untuk tool destruktif. Return True kalau diizinkan.

        Opsi:
        - y: izinkan tool ini, ingat untuk sisa session (ga nanya lagi)
        - a: izinkan SEMUA tool untuk sisa session
        - n: tolak
        """
        if self._allow_all:
            return True
        if tool_name in self._allowed_tools:
            return True

        self._stop_all()
        args_str = _format_args(arguments)
        self.console.print(f"  [yellow]⚡ {tool_name}[/yellow][dim]({args_str})[/dim] — {description}")
        choice = Prompt.ask(
            "  [yellow]Izinkan?[/yellow]",
            choices=["y", "a", "n"],
            default="y",
            console=self.console,
        )
        if choice == "a":
            self._allow_all = True
            self.console.print("  [dim]Semua tool diizinkan untuk session ini.[/dim]")
            return True
        if choice == "y":
            self._allowed_tools.add(tool_name)
            self.console.print(f"  [dim]{tool_name} diizinkan untuk session ini.[/dim]")
            return True
        return False

    def permission_status(self) -> dict[str, Any]:
        """Return status permission untuk display."""
        return {
            "allow_all": self._allow_all,
            "allowed_tools": sorted(self._allowed_tools),
        }

    def reset_permissions(self) -> None:
        """Reset semua permission — berguna setelah /reset."""
        self._allow_all = False
        self._allowed_tools.clear()

    # ------------------------------------------------------------------ #
    # Todo list
    # ------------------------------------------------------------------ #

    def show_todos(self, todos: list[dict]) -> None:
        if not todos:
            return
        icons = {"pending": "[dim]○[/dim]", "in_progress": "[yellow]◐[/yellow]", "completed": "[green]●[/green]"}
        lines = []
        for t in todos:
            icon = icons.get(t.get("status", "pending"), "[dim]○[/dim]")
            lines.append(f"  {icon} {t.get('content', '')}")
        self.console.print(Panel(Group(*lines), title="[bold]todo[/bold]", border_style="blue"))

    # ------------------------------------------------------------------ #
    # Context status
    # ------------------------------------------------------------------ #

    def show_context_status(self, info: dict) -> None:
        """Tampilkan context window usage: tokens, %, prompt/completion stats."""
        tokens = info["tokens"]
        pct = info["pct"]
        window = info["window"]
        prompt_t = info.get("prompt_tokens", 0)
        comp_t = info.get("completion_tokens", 0)

        if pct < 50:
            color = "green"
        elif pct < 80:
            color = "yellow"
        else:
            color = "red"

        bar_len = 20
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)

        self.console.print(
            f"  [dim]Context[/dim] [{color}]{bar}[/{color}] "
            f"[{color}]{tokens:,}[/{color}][dim]/{window:,} tokens "
            f"({pct:.0f}%)[/dim]  "
            f"[dim]prompt: {prompt_t:,} | completion: {comp_t:,}[/dim]"
        )

    # ------------------------------------------------------------------ #
    # Final response panel
    # ------------------------------------------------------------------ #

    def show_response(self, resp: "ModelResponse") -> None:
        if not resp.content:
            return
        if self._did_stream:
            return  # text udah tampil via streaming Live, jangan double
        title = f"autokeren [{resp.model_id}]" if resp.model_id else "autokeren"
        self.console.print(Panel(resp.content, title=title))

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #

    def cleanup(self) -> None:
        self._stop_all()

    def _stop_all(self) -> None:
        self._stop_status()
        self._stop_live()

    def _stop_status(self) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None

    def _stop_live(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #


def _format_args(arguments: dict) -> str:
    parts: list[str] = []
    for k, v in arguments.items():
        if isinstance(v, str):
            s = v
        else:
            s = json.dumps(v, default=str)
        if len(s) > 60:
            s = s[:57] + "…"
        parts.append(f"{k}={s}")
    return ", ".join(parts)


def _summarize_output(output: object) -> str:
    if output is None:
        return ""
    if isinstance(output, dict):
        if "content" in output:
            lines = str(output["content"]).count("\n") + 1
            return f"{lines} baris"
        if "path" in output:
            return str(output["path"])
        if "backup" in output:
            return f"tersimpan (backup: {output['backup']})"
        compact = json.dumps(output, default=str)
        return compact[:80] + "…" if len(compact) > 80 else compact
    text = str(output).strip().replace("\n", " ")
    if len(text) > 80:
        return f"{len(text)} chars"
    return text
