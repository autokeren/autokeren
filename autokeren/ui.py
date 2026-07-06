"""Rich-based UI untuk autokeren CLI — banner, streaming, tool display, permission, todo."""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import pyfiglet
from rich._spinners import SPINNERS  # type: ignore
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status
from rich.text import Text
from rich.theme import Theme

SPINNERS["mikir"] = {"interval": 350, "frames": ["mikir .  ", "mikir .. ", "mikir ..."]}

if TYPE_CHECKING:
    from autokeren.models.base import ModelResponse
    from autokeren.tools.base import ToolResult

# Tema warna: ijo, merah, putih, biru telur asin (#4FC3F7)
AK_THEME = Theme({
    "markdown.h1": "bold green",
    "markdown.h2": "bold green",
    "markdown.h3": "bold #4FC3F7",
    "markdown.h4": "#4FC3F7",
    "markdown.h5": "dim #4FC3F7",
    "markdown.h6": "dim #4FC3F7",
    "markdown.h1.bar": "dim #555555",
    "markdown.h2.bar": "dim #555555",
    "markdown.bold": "bold white",
    "markdown.italic": "italic white",
    "markdown.code": "#4FC3F7",
    "markdown.code_block": "on #1a1a2e",
    "markdown.link": "underline #4FC3F7",
    "markdown.list": "white",
    "markdown.table.header": "bold green",
    "markdown.table.border": "#4FC3F7",
    "markdown.block_quote": "italic yellow",
    "markdown.hr": "dim #555555",
})

if TYPE_CHECKING:
    from autokeren.models.base import ModelResponse
    from autokeren.tools.base import ToolResult

_MERMAID_RE = re.compile(r"```mermaid\s*\n.*?```", re.DOTALL)


class AgentUI:
    """UI layer untuk autokeren. Pure presentational, no business logic.

    Style: opencode-inspired — inline streaming, compact tool display.
    """

    def __init__(self, console: Console):
        self.console = console
        self._status: Status | None = None
        self._live: Live | None = None
        self._stream_text: str = ""
        self._did_stream: bool = False
        self._allow_all: bool = False
        self._allowed_tools: set[str] = set()
        self._last_render_time: float = 0.0
        self.mermaid_render: bool = False
        self._last_mermaid_blocks: list[str] = []

    # ------------------------------------------------------------------ #
    # Banner
    # ------------------------------------------------------------------ #

    def show_banner(self, version: str = "0.4.3") -> None:
        full_art = pyfiglet.figlet_format("AUTOKEREN", font="slant").rstrip("\n").split("\n")
        auto_art = pyfiglet.figlet_format("AUTO", font="slant").rstrip("\n").split("\n")
        colored = Text()
        for full_line, auto_line in zip(full_art, auto_art):
            split_at = len(auto_line.rstrip())
            colored.append(full_line[:split_at], style="bold #FF0000")
            colored.append(full_line[split_at:], style="bold white")
            colored.append("\n")
        tagline = Text("Cloudflare-first agentic coding CLI buat developer Indonesia", style="dim italic")
        ver = Text(f"v{version}", style="bold yellow")
        self.console.print(Align.center(colored))
        self.console.print(Align.center(Group(tagline, ver)))

    # ------------------------------------------------------------------ #
    # Model thinking + streaming (inline, no panel)
    # ------------------------------------------------------------------ #

    def on_model_start(self) -> None:
        self._stop_all()
        self._stream_text = ""
        self._did_stream = False
        self._status = self.console.status("[dim]mikir[/dim]", spinner="mikir")
        self._status.start()

    def on_chunk(self, text: str) -> None:
        if self._status is not None:
            self._stop_status()
            self._live = Live(
                Text(""),
                console=self.console,
                refresh_per_second=12,
                vertical_overflow="visible",
                transient=False,
            )
            self._live.start()
        self._did_stream = True
        self._stream_text += text
        if self._live is not None:
            import time
            now = time.monotonic()
            if now - self._last_render_time >= 0.08:
                self._last_render_time = now
                self._live.update(Markdown(self._stream_text, code_theme="monokai"))

    def _final_render(self) -> None:
        """Final render sebelum stop Live — pastikan content lengkap."""
        if self._live is not None and self._stream_text.strip():
            self._live.update(Markdown(self._stream_text, code_theme="monokai"))

    def on_model_end(self, resp: "ModelResponse") -> None:
        self._final_render()
        self._stop_all()

    def show_response(self, resp: "ModelResponse") -> None:
        if not resp.content:
            return
        if self._did_stream and self._stream_text.strip():
            self.console.print(_sep())
            self._stream_text = ""
            self._did_stream = False
            return
        self.console.print(_sep())
        _render_markdown(resp.content, self.console, mermaid_render=self.mermaid_render, store_blocks=self)
        self.console.print(_sep())

    # ------------------------------------------------------------------ #
    # Tool execution — opencode style: ⏺ call line, ✓ result line
    # ------------------------------------------------------------------ #

    def on_tool_start(self, name: str, arguments: dict) -> None:
        self._final_render()
        self._stop_all()
        self._stream_text = ""
        label = _format_tool_call(name, arguments)
        self.console.print(f"  [bold cyan]⏺[/bold cyan] {label}")
        self._status = self.console.status("  [dim]…[/dim]", spinner="dots")
        self._status.start()

    def on_tool_end(self, name: str, result: "ToolResult") -> None:
        self._stop_status()
        if result.ok:
            summary = _summarize_tool_result(name, result.output)
            self.console.print(f"  [green]✓[/green] [dim]{summary}[/dim]")
        else:
            err = result.error or "gagal"
            self.console.print(f"  [red]✗[/red] [red]{err}[/red]")

    def on_tool_output(self, name: str, line: str) -> None:
        self._stop_status()
        self.console.print(f"  [dim]│[/dim] {line}")

    # ------------------------------------------------------------------ #
    # Permission system
    # ------------------------------------------------------------------ #

    def confirm_permission(self, tool_name: str, description: str, arguments: dict) -> bool:
        if self._allow_all:
            return True
        if tool_name in self._allowed_tools:
            return True

        self._stop_all()
        label = _format_tool_call(tool_name, arguments)
        self.console.print(f"  [yellow]⚡ {label}[/yellow] — {description}")
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
            return True
        return False

    def permission_status(self) -> dict[str, Any]:
        return {
            "allow_all": self._allow_all,
            "allowed_tools": sorted(self._allowed_tools),
        }

    def reset_permissions(self) -> None:
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
    # Status bar — compact one-liner before prompt
    # ------------------------------------------------------------------ #

    def show_status_bar(self, info: dict) -> None:
        model = info.get("model", "?")
        pct = info.get("pct", 0)
        cwd = info.get("cwd", "?")
        neurons_remaining = info.get("neurons_remaining")
        neurons_quota = info.get("neurons_quota")

        if pct < 50:
            color = "green"
        elif pct < 80:
            color = "yellow"
        else:
            color = "red"

        bar_len = 10
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)

        from datetime import datetime
        now = datetime.now().strftime("%H:%M")

        neuron_str = ""
        if neurons_remaining is not None and neurons_quota:
            neurons_used = neurons_quota - neurons_remaining
            n_pct = (neurons_used / neurons_quota) * 100 if neurons_quota else 0
            if n_pct > 80:
                n_color = "red"
            elif n_pct > 50:
                n_color = "yellow"
            else:
                n_color = "green"
            neuron_str = f" [dim]|[/dim] [{n_color}]neurons {neurons_used:,}/{neurons_quota:,} ({n_pct:.0f}%)[/{n_color}]"

        self.console.print(
            f"  [dim][{color}]{model}[/{color}] "
            f"ctx [{color}]{bar}[/{color}] {pct:.0f}% "
            f"[dim]| {cwd} | {now}[/dim]{neuron_str}"
        )

    # ------------------------------------------------------------------ #
    # Context status — detailed, after response
    # ------------------------------------------------------------------ #

    def show_context_status(self, info: dict) -> None:
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
    # Diagram rendering
    # ------------------------------------------------------------------ #

    def render_last_diagram(self) -> None:
        """Render diagram terakhir sebagai image (dipanggil via /diagram)."""
        if not self._last_mermaid_blocks:
            self.console.print("[dim]Belum ada diagram di session ini.[/dim]")
            return
        self.console.print()
        for i, block in enumerate(self._last_mermaid_blocks):
            self.console.print(f"  [bold blue]🖼️ Diagram {i + 1}[/bold blue]")
            from autokeren.mermaid import _try_render_image, render_mermaid_text
            if not _try_render_image(block, self.console):
                render_mermaid_text(block, self.console)
            self.console.print()

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


def _sep() -> Text:
    """Separator line abu-abu tipis."""
    return Text("─" * 60, style="dim #555555")


def _render_markdown(text: str, console: Console, mermaid_render: bool = False, store_blocks: "AgentUI | None" = None) -> None:
    """Render text sebagai rich Markdown dengan tema autokeren.

    Mermaid blocks di-strip dulu, dirender terpisah sebagai diagram (kalau mermaid_render=True).
    """
    mermaid_blocks = _MERMAID_RE.findall(text)
    clean_text = _MERMAID_RE.sub("", text).strip()

    if store_blocks is not None:
        store_blocks._last_mermaid_blocks = mermaid_blocks

    if clean_text:
        md = Markdown(clean_text, code_theme="monokai")
        console.print(md)

    if mermaid_render and mermaid_blocks:
        from autokeren.mermaid import extract_and_render
        extract_and_render(text, console)


def _format_tool_call(name: str, arguments: dict) -> str:
    key = _key_arg(name, arguments)
    if key:
        return f"[bold]{name}[/bold]  [dim]{key}[/dim]"
    return f"[bold]{name}[/bold]"


def _key_arg(name: str, arguments: dict) -> str:
    if name in ("write_file", "read_file", "patch_file"):
        return str(arguments.get("path", "?"))
    if name == "run_shell":
        cmd = str(arguments.get("command", ""))
        return cmd if len(cmd) <= 70 else cmd[:67] + "…"
    if name == "search_code":
        return str(arguments.get("pattern", "?"))
    if name == "list_files":
        return str(arguments.get("path", "."))
    if name == "git_commit":
        msg = str(arguments.get("message", ""))
        return msg if len(msg) <= 60 else msg[:57] + "…"
    if name == "fetch_url":
        return str(arguments.get("url", "?"))
    if name in ("cf_deploy", "cf_build_next"):
        return str(arguments.get("target", arguments.get("path", "?")))
    if name == "cf_kv":
        return f"{arguments.get('action', '?')} {arguments.get('namespace_id', '')}"
    if name == "cf_d1":
        action = arguments.get("action", "?")
        return f"{action}" if action != "query" else f"query {arguments.get('database_id', '')[:12]}"
    if name == "tmux":
        return f"{arguments.get('action', '?')} {arguments.get('session', '')}".strip()
    if name == "camofox":
        return str(arguments.get("action", "?"))
    return _format_args(arguments)


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


def _summarize_tool_result(name: str, output: object) -> str:
    if output is None:
        return name
    if isinstance(output, dict):
        if name == "write_file":
            path = output.get("path", "?")
            lines = output.get("lines", 0)
            return f"menulis {lines} baris → {path}"
        if name == "read_file":
            lines = output.get("total_lines", 0)
            path = output.get("path", "?")
            return f"membaca {lines} baris dari {path}"
        if name == "patch_file":
            path = output.get("path", "?")
            return f"mengedit {path}"
        if name == "list_files":
            text = str(output).strip()
            count = text.count("\n") + 1 if text else 0
            return f"{count} file"
        if name == "search_code":
            text = str(output).strip()
            count = text.count("\n") + 1 if text else 0
            return f"{count} hasil"
        if name == "run_shell":
            text = str(output).strip().replace("\n", " ")
            return text[:80] + "…" if len(text) > 80 else text or "selesai"
        if name == "git_status":
            text = str(output).strip().replace("\n", " ")
            return text[:80] + "…" if len(text) > 80 else text or "clean"
        if name == "git_diff":
            text = str(output).strip()
            lines = text.count("\n") + 1 if text else 0
            return f"{lines} baris diff"
        if name == "git_commit":
            return "committed"
        if name == "fetch_url":
            text = str(output).strip()
            return f"{len(text)} chars"
        if "path" in output:
            return str(output["path"])
        compact = json.dumps(output, default=str)
        return compact[:80] + "…" if len(compact) > 80 else compact
    text = str(output).strip().replace("\n", " ")
    if len(text) > 80:
        return f"{len(text)} chars"
    return text or name
