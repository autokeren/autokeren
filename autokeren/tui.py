"""TUI (Text User Interface) untuk autokeren berbasis Textual."""
from __future__ import annotations

import threading
import queue
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Container
from textual.widgets import Static, Input, OptionList
from textual.screen import ModalScreen
from textual.binding import Binding
from rich.markdown import Markdown
from rich.text import Text


from autokeren.agent import Agent
from autokeren.config import Config
from autokeren.models.base import ModelResponse
from autokeren.ui import _format_tool_call, _summarize_tool_result


class ThinkingWidget(Static):
    """Widget untuk animasi 'mikir...'."""

    def on_mount(self) -> None:
        self.frame = 0
        self.frames = [
            "🤔 [dim]mikir .  [/dim]",
            "🤔 [dim]mikir .. [/dim]",
            "🤔 [dim]mikir ...[/dim]",
            "🤔 [dim]mikir  ..[/dim]",
            "🤔 [dim]mikir   .[/dim]",
        ]
        self.update(self.frames[0])
        self.timer = self.set_interval(0.3, self.next_frame)

    def next_frame(self) -> None:
        self.frame = (self.frame + 1) % len(self.frames)
        self.update(self.frames[self.frame])


class ModelSelectScreen(ModalScreen[str]):
    """Screen Modal untuk memilih model AI secara interaktif."""

    def __init__(self, models: list[dict[str, Any]], current_model: str) -> None:
        super().__init__()
        self.models = models
        self.current_model = current_model

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold green]PILIH MODEL AI[/bold green]", id="modal-title"),
            OptionList(id="model-list"),
            id="modal-dialog",
        )

    def on_mount(self) -> None:
        option_list = self.query_one("#model-list", OptionList)
        for m in self.models:
            label = m.get("name", m["id"])
            if m["id"] == self.current_model:
                label = f"✨ [green]{label} (Aktif)[/green]"
            option_list.add_option(label)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        chosen_id = self.models[event.option_index]["id"]
        self.dismiss(chosen_id)


    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.dismiss(None)


class PermissionSelectScreen(ModalScreen[str]):
    """Screen Modal untuk meminta izin eksekusi tool."""

    def __init__(self, tool_call_label: str, description: str) -> None:
        super().__init__()
        self.tool_call_label = tool_call_label
        self.description = description

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold yellow]IZIN EKSEKUSI TOOL[/bold yellow]", id="modal-title"),
            Static(f"[bold]{self.tool_call_label}[/bold]\n[dim]{self.description}[/dim]", id="modal-desc"),
            OptionList(
                "✓ Izinkan Sekali",
                "⚡ Izinkan Semua Tool Sesi Ini",
                "✗ Tolak Eksekusi",
                id="perm-list"
            ),
            id="modal-dialog-perm",
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        choices = ["y", "a", "n"]
        self.dismiss(choices[event.option_index])

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.dismiss("n")


class ApprovalSelectScreen(ModalScreen[bool]):
    """Screen Modal untuk menyetujui rencana kerja."""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold yellow]SETUJUI RENCANA KERJA?[/bold yellow]", id="modal-title"),
            OptionList(
                "✓ Setujui Rencana",
                "✗ Tolak Rencana",
                id="approve-list"
            ),
            id="modal-dialog-approve",
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        choices = [True, False]
        self.dismiss(choices[event.option_index])

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.dismiss(False)



class StatusWidget(Static):
    """Widget untuk menampilkan informasi status di panel kiri."""

    def __init__(self, agent: Agent, cfg: Config) -> None:
        super().__init__()
        self.agent = agent
        self.cfg = cfg

    def on_mount(self) -> None:
        self.update_status()

    def update_status(self) -> None:
        info = self.agent.status_bar_info()
        ctx = self.agent.context_info()

        model = info.get("model", "?")
        cwd = info.get("cwd", "?")
        neurons_remaining = info.get("neurons_remaining")
        neurons_quota = info.get("neurons_quota")

        if neurons_remaining is not None and neurons_quota:
            neurons_str = f"{neurons_quota - neurons_remaining:,}/{neurons_quota:,}"
        else:
            neurons_str = "-"

        sisa_tokens = ctx["window"] - ctx["tokens"] if ctx["window"] > 0 else 0

        res = f"""[bold yellow]STATUS[/bold yellow]

[bold]Model[/bold]   : {model}
[bold]Auth[/bold]    : {self.cfg.auth.mode}
[bold]Tokens[/bold]  : {ctx['tokens']:,} ({ctx['pct']:.1f}%)
[bold]Sisa Tok[/bold]: {sisa_tokens:,}
[bold]Neurons[/bold] : {neurons_str}

[bold]Active[/bold]  : {cwd}
[bold]Session[/bold] : {self.agent.context.summary().get('messages', 0)} msg

[bold]Temp[/bold]    : {self.cfg.cloudflare.temperature}
[bold]MaxTok[/bold]  : {self.cfg.cloudflare.max_tokens}

[bold]P.Mode[/bold]  : {self.cfg.autokeren.plan_mode}
[bold]M.Calls[/bold] : {self.agent._tool_call_count}/{self.cfg.autokeren.max_tool_calls or 'unlimited'}

[dim]Klik di sini untuk ganti model[/dim]"""
        try:
            self.update(Text.from_markup(res))
        except Exception:
            self.update(res)


    async def on_click(self) -> None:
        # Klik pada panel status memicu aksi pemilihan model
        await self.app.action_model()  # type: ignore



class MessageWidget(Static):
    """Widget untuk menampilkan pesan user/assistant/system."""

    def __init__(self, role: str, content: str = "") -> None:
        super().__init__()
        self.role = role
        self.msg_content = content

    def on_mount(self) -> None:
        self.update_content(self.msg_content)

    def update_content(self, new_content: str) -> None:
        self.msg_content = new_content
        if self.role == "user":
            tx = Text()
            tx.append("kamu: ", style="bold blue")
            tx.append(self.msg_content)
            self.update(tx)
        elif self.role == "system":
            try:
                self.update(Text.from_markup(self.msg_content))
            except Exception:
                self.update(self.msg_content)
        else:
            self.update(Markdown(self.msg_content or "..."))




class ToolWidget(Static):
    """Widget untuk menampilkan jalannya tool secara inline."""

    def __init__(self, name: str, arguments: dict) -> None:
        super().__init__()
        self.tool_name: str = name
        self.arguments = arguments
        self.status = "running"
        self.result_summary = ""
        self.output_lines: list[str] = []

    def update_status(self, status: str, summary: str = "") -> None:
        self.status = status
        self.result_summary = summary
        self.refresh()

    def append_line(self, line: str) -> None:
        self.output_lines.append(line)
        self.refresh()

    def render(self) -> Text:
        res = Text()
        label = _format_tool_call(self.tool_name, self.arguments)
        
        if self.status == "running":
            res.append("  ⏺ ", style="bold cyan")
            res.append(label)
        elif self.status == "success":
            res.append("  ✓ ", style="green")
            res.append(self.result_summary, style="dim")
        else:
            res.append("  ✗ ", style="red")
            res.append(self.result_summary, style="red")
            
        if self.output_lines:
            for line in self.output_lines:
                res.append("\n")
                res.append("  │ ", style="dim")
                res.append(line)
        return res




class AutokerenTUI(App):
    """Aplikasi Full TUI untuk autokeren bergaya Antigravity."""

    CSS = """
    Screen {
        layout: vertical;
        background: $background;
    }
    Horizontal {
        height: 100%;
        width: 100%;
    }
    #status-pane {
        width: 32;
        height: 100%;
        border: round #555555;
        padding: 1 1;
    }
    #right-layout {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }
    #chat-pane {
        height: 1fr;
        width: 100%;
        border: round #555555;
        padding: 0 1;
    }
    #chat-area {
        height: auto;
        padding-bottom: 2;
    }
    #input-pane {
        height: 3;
        width: 100%;
        border: round #555555;
        margin: 0;
    }
    MessageWidget {
        height: auto;
        margin: 1 0;
    }
    ToolWidget {
        height: auto;
        margin: 0;
    }
    ThinkingWidget {
        height: auto;
        margin: 1 0;
    }
    ModelSelectScreen, PermissionSelectScreen, ApprovalSelectScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }
    #modal-dialog {
        width: 50;
        height: 14;
        border: double #555555;
        background: $panel;
        padding: 1 2;
    }
    #modal-dialog-perm {
        width: 55;
        height: 14;
        border: double #555555;
        background: $panel;
        padding: 1 2;
    }
    #modal-dialog-approve {
        width: 40;
        height: 10;
        border: double #555555;
        background: $panel;
        padding: 1 2;
    }
    #modal-desc {
        margin-bottom: 1;
        height: auto;
    }
    #modal-title {
        text-align: center;
        margin-bottom: 1;
    }
    #model-list, #perm-list, #approve-list {
        height: 1fr;
    }

    """

    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("f2", "model", "Ganti Model"),
        Binding("f3", "reset", "Reset Sesi"),
        Binding("f4", "copy_last", "Salin Respon"),
        Binding("f5", "compact", "Compact Context"),
        Binding("ctrl+q", "quit", "Keluar"),

    ]

    def __init__(self, agent: Agent, cfg: Config) -> None:
        super().__init__()
        self.agent = agent
        self.cfg = cfg
        self.input_mode = "chat"
        self.allow_all = False
        self.allowed_tools: set[str] = set()

        # Shared thread-safe structures
        self.permission_queue: queue.Queue[tuple[bool, bool]] = queue.Queue()
        self.approval_queue: queue.Queue[bool] = queue.Queue()

        # Current active widgets
        self.thinking_widget: ThinkingWidget | None = None
        self.current_assistant_widget: MessageWidget | None = None
        self.current_tool_widget: ToolWidget | None = None

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Container(StatusWidget(self.agent, self.cfg), id="status-pane"),
            Container(
                VerticalScroll(Container(id="chat-area"), id="chat-pane"),
                Input(id="input-pane", placeholder="✍️ Ketik pesan di sini..."),
                id="right-layout"
            )
        )


    def on_mount(self) -> None:
        # Bind Agent callbacks ke TUI
        self.agent.on_model_start = self.on_model_start
        self.agent.on_model_end = self.on_model_end
        self.agent.on_tool_start = self.on_tool_start
        self.agent.on_tool_end = self.on_tool_end
        self.agent.on_tool_output = self.on_tool_output
        self.agent.on_chunk = self.on_chunk
        self.agent.permission_callback = self.confirm_permission

        # Tampilkan welcome banner
        import pyfiglet
        from autokeren import __version__
        from rich.markup import escape

        full_art = pyfiglet.figlet_format("AUTOKEREN", font="slant").rstrip("\n").split("\n")
        mid = len(full_art) // 2
        colored_lines = []
        for i, line in enumerate(full_art):
            line_esc = escape(line)
            if i < mid:
                colored_lines.append(f"[bold red]{line_esc}[/bold red]")
            else:
                extra = f"  [bold yellow]v{__version__}[/bold yellow]" if i == mid else ""
                colored_lines.append(f"[bold white]{line_esc}[/bold white]{extra}")
        
        welcome = (
            "\n".join(colored_lines) + "\n\n"
            "Ketik pertanyaan kamu di bawah, atau tekan [bold]F1[/bold] untuk bantuan perintah."
        )
        self.append_chat_message("system", welcome)
        self.update_status()



    # ------------------------------------------------------------------ #
    # Agent Thread-safe Callbacks
    # ------------------------------------------------------------------ #

    def on_model_start(self) -> None:
        def _start():
            self.thinking_widget = ThinkingWidget()
            self.query_one("#chat-area").mount(self.thinking_widget)
            self.scroll_chat_to_end()
        self.call_from_thread(_start)

    def on_chunk(self, text: str) -> None:
        def _chunk():
            # Hapus animasi mikir jika ada sebelum memount widget streaming text
            if self.thinking_widget:
                self.thinking_widget.remove()
                self.thinking_widget = None
                self.current_assistant_widget = MessageWidget("assistant", "")
                self.query_one("#chat-area").mount(self.current_assistant_widget)

            if self.current_assistant_widget:
                self.current_assistant_widget.update_content(self.current_assistant_widget.msg_content + text)
                self.scroll_chat_to_end()
        self.call_from_thread(_chunk)

    def on_model_end(self, resp: ModelResponse) -> None:
        def _end():
            if self.thinking_widget:
                self.thinking_widget.remove()
                self.thinking_widget = None
            self.current_assistant_widget = None
            self.update_status()
        self.call_from_thread(_end)

    def on_tool_start(self, name: str, arguments: dict) -> None:
        def _tool():
            self.current_tool_widget = ToolWidget(name, arguments)
            self.query_one("#chat-area").mount(self.current_tool_widget)
            self.scroll_chat_to_end()
        self.call_from_thread(_tool)

    def on_tool_output(self, name: str, line: str) -> None:
        def _output():
            if self.current_tool_widget:
                self.current_tool_widget.append_line(line)
                self.scroll_chat_to_end()
        self.call_from_thread(_output)

    def on_tool_end(self, name: str, result: Any) -> None:
        def _end():
            if self.current_tool_widget:
                ok = result.ok if hasattr(result, "ok") else True
                output = result.output if hasattr(result, "output") else result
                error = result.error if hasattr(result, "error") else None
                status = "success" if ok else "error"
                summary = _summarize_tool_result(name, output) if ok else (error or "gagal")
                self.current_tool_widget.update_status(status, summary)
                self.current_tool_widget = None
                self.scroll_chat_to_end()
                self.update_status()
        self.call_from_thread(_end)

    def confirm_permission(self, tool_name: str, description: str, arguments: dict) -> bool:
        if self.allow_all:
            return True
        if tool_name in self.allowed_tools:
            return True

        # Kita harus prompt user di thread utama TUI. Block thread agent saat ini.
        evt = threading.Event()
        result = [False]

        def _prompt():
            from rich.markup import escape
            label = _format_tool_call(tool_name, arguments)
            label_esc = escape(label)
            desc_esc = escape(description)
            self.append_chat_message("system", f"⚡ Panggil [bold cyan]{label_esc}[/bold cyan]? — {desc_esc}")

            def on_perm_result(choice: str | None) -> None:
                from rich.markup import escape
                allowed = False
                name_esc = escape(tool_name)
                if choice == "y":
                    allowed = True
                    self.allowed_tools.add(tool_name)
                    self.append_chat_message("system", f"Tool [bold cyan]{name_esc}[/bold cyan] diizinkan.")
                elif choice == "a":
                    allowed = True
                    self.allow_all = True
                    self.append_chat_message("system", "Semua tool diizinkan untuk sesi ini.")
                else:
                    self.append_chat_message("system", f"Tool [bold red]{name_esc}[/bold red] ditolak.")

                result[0] = allowed
                evt.set()

            self.push_screen(PermissionSelectScreen(label, description), on_perm_result)

        self.call_from_thread(_prompt)
        evt.wait()
        return result[0]



    # ------------------------------------------------------------------ #
    # Helper & UI Actions
    # ------------------------------------------------------------------ #

    def append_chat_message(self, role: str, content: str) -> None:
        widget = MessageWidget(role, content)
        self.query_one("#chat-area").mount(widget)
        self.scroll_chat_to_end()

    def scroll_chat_to_end(self) -> None:
        chat_pane = self.query_one("#chat-pane", VerticalScroll)
        chat_pane.scroll_to(y=chat_pane.max_scroll_y, animate=False)

    def update_status(self) -> None:
        self.query_one("#status-pane StatusWidget", StatusWidget).update_status()

    # ------------------------------------------------------------------ #
    # Input Submission Handler
    # ------------------------------------------------------------------ #

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        if not val:
            return

        input_pane = self.query_one("#input-pane", Input)
        input_pane.value = ""

        if val.startswith("/"):
            await self.handle_slash_command(val)
            return

        self.append_chat_message("user", val)
        input_pane.disabled = True
        input_pane.placeholder = "Sedang berpikir..."
        
        # Jalankan agent loop di background worker thread
        self.run_worker(self._run_agent_flow(val), thread=True)


    async def _run_agent_flow(self, user_input: str) -> None:
        try:
            # Panggil Agent loop
            self.agent.run(user_input)

            # Jika Plan Mode aktif dan rencana belum disetujui
            while self.cfg.autokeren.plan_mode and not self.agent.plan_approved:
                approved = await self.prompt_plan_approval()
                if approved:
                    self.agent.approve_plan()
                    self.agent.run("")
                else:
                    self.agent.context.add_user("User menolak rencana. Tanya apa yang perlu diubah.")
                    self.agent.run("")

        except Exception as e:
            self.append_chat_message("system", f"[red]Error saat menjalankan agent: {e}[/red]")
        finally:
            def _reset_input():
                input_pane = self.query_one("#input-pane", Input)
                input_pane.disabled = False
                input_pane.placeholder = "✍️ Ketik pesan di sini..."
                input_pane.focus()
                self.update_status()
            self.call_from_thread(_reset_input)

    async def prompt_plan_approval(self) -> bool:
        evt = threading.Event()
        result = [False]

        def _prompt():
            def on_approve_result(approved: bool | None) -> None:
                res = approved if approved is not None else False
                if res:
                    self.append_chat_message("system", "Rencana kerja disetujui.")
                else:
                    self.append_chat_message("system", "Rencana kerja ditolak.")
                result[0] = res
                evt.set()

            self.push_screen(ApprovalSelectScreen(), on_approve_result)

        self.call_from_thread(_prompt)
        evt.wait()
        return result[0]


    # ------------------------------------------------------------------ #
    # Key Bindings & Slash Commands
    # ------------------------------------------------------------------ #

    async def action_help(self) -> None:
        help_text = (
            "[bold yellow]BANTUAN KEY BINDING & SLASH COMMANDS[/bold yellow]\n\n"
            "Tombol Pintas:\n"
            "  - [bold]F1[/bold]   : Bantuan ini\n"
            "  - [bold]F2[/bold]   : Tampilkan & Ganti Model aktif\n"
            "  - [bold]F3[/bold]   : Reset Sesi percakapan\n"
            "  - [bold]F4[/bold]   : Salin respon terakhir AI ke clipboard\n"
            "  - [bold]F5[/bold]   : Compact Context (ringkas percakapan lama)\n"
            "  - [bold]Ctrl+Q[/bold]: Keluar dari aplikasi\n\n"
            "Perintah Slash:\n"
            "  - [bold]/model <nama>[/bold]: Ganti model aktif\n"
            "  - [bold]/compact[/bold]     : Meringkas riwayat context\n"
            "  - [bold]/reset[/bold]       : Reset seluruh sesi chat\n"
            "  - [bold]/permissions[/bold] : Cek daftar izin tool\n"
            "  - [bold]/memory[/bold]      : Tampilkan memory proyek\n"
            "  - [bold]/sessions[/bold]    : Tampilkan saved sessions\n"
            "  - [bold]/save <nama>[/bold]  : Simpan sesi obrolan saat ini\n"
            "  - [bold]/resume <id>[/bold]  : Resume sesi obrolan lama\n"
            "  - [bold]/q[/bold]            : Keluar dari aplikasi"
        )
        self.append_chat_message("system", help_text)

    async def action_model(self) -> None:
        from autokeren.models.cloudflare import fetch_available_models
        all_models = fetch_available_models(self.cfg)
        current_model = self.agent.router.current_model_id()

        def on_select(chosen_id: str | None) -> None:
            if chosen_id:
                from autokeren.models.cloudflare import resolve_model_id
                resolved = resolve_model_id(chosen_id, self.agent.router.models[0].auth_mode)
                if self.agent.router.switch_model(resolved):
                    self.append_chat_message("system", f"Model aktif diganti ke: [bold]{chosen_id}[/bold]")
                    self.update_status()
                else:
                    self.append_chat_message("system", f"[red]Model '{chosen_id}' tidak ditemukan.[/red]")

        self.push_screen(ModelSelectScreen(all_models, current_model), on_select)

    async def action_copy_last(self) -> None:
        last_assistant_msg = None
        for msg in reversed(self.agent.context.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                last_assistant_msg = msg["content"]
                break
        
        if last_assistant_msg:
            try:
                self.copy_to_clipboard(last_assistant_msg)
                self.append_chat_message("system", "✓ Respon terakhir berhasil disalin ke clipboard.")
            except Exception as e:
                self.append_chat_message("system", f"[red]Gagal menyalin ke clipboard: {e}[/red]")
        else:
            self.append_chat_message("system", "Belum ada respon assistant untuk disalin.")

    async def action_reset(self) -> None:

        self.agent.reset()
        self.allow_all = False
        self.allowed_tools.clear()
        
        # Hapus widget chat
        chat_area = self.query_one("#chat-area")
        for child in list(chat_area.children):
            child.remove()
            
        self.append_chat_message("system", "Sesi dan izin tool berhasil direset.")
        self.update_status()

    async def action_compact(self) -> None:
        self.append_chat_message("system", "Meringkas context percakapan...")
        try:
            msg = self.agent.compact()
            self.append_chat_message("system", f"[green]{msg}[/green]")
            self.update_status()
        except Exception as e:
            self.append_chat_message("system", f"[red]Compact gagal: {e}[/red]")

    async def handle_slash_command(self, cmd_line: str) -> None:
        parts = cmd_line.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/q", "/quit"):
            self.exit()
        elif cmd == "/help":
            await self.action_help()
        elif cmd == "/reset":
            await self.action_reset()
        elif cmd == "/compact":
            await self.action_compact()
        elif cmd == "/permissions":
            if self.allow_all:
                self.append_chat_message("system", "Semua tool diizinkan untuk sesi ini.")
            elif self.allowed_tools:
                self.append_chat_message("system", f"Tool diizinkan: {', '.join(sorted(self.allowed_tools))}")
            else:
                self.append_chat_message("system", "Belum ada tool yang diizinkan.")
        elif cmd == "/memory":
            mem = self.agent.memory.load()
            if mem:
                self.append_chat_message("system", f"[bold magenta]MEMORY PROYEK:[/bold magenta]\n{mem}")
            else:
                self.append_chat_message("system", "Memory kosong.")
        elif cmd == "/model":
            if not arg:
                await self.action_model()
            else:
                from autokeren.models.cloudflare import resolve_model_id
                resolved = resolve_model_id(arg, self.agent.router.models[0].auth_mode)
                if self.agent.router.switch_model(resolved):
                    self.append_chat_message("system", f"Model aktif diganti ke: [bold]{arg}[/bold]")
                    self.update_status()
                else:
                    self.append_chat_message("system", f"[red]Model '{arg}' tidak ditemukan.[/red]")
        elif cmd == "/save":
            name = arg or f"session-{len(self.agent.sessions.list()) + 1}"
            try:
                sid = self.agent.save_session(name)
                self.append_chat_message("system", f"[green]Sesi '{name}' disimpan. ID: {sid}[/green]")
            except Exception as e:
                self.append_chat_message("system", f"[red]Save gagal: {e}[/red]")
        elif cmd == "/resume":
            if not arg:
                self.append_chat_message("system", "Gunakan: [bold]/resume <nama|id>[/bold]")
            else:
                try:
                    msg = self.agent.resume_session(arg)
                    self.append_chat_message("system", f"[green]{msg}[/green]")
                    self.rebuild_chat_history()
                    self.update_status()
                except Exception as e:
                    self.append_chat_message("system", f"[red]Resume gagal: {e}[/red]")
        elif cmd == "/sessions":
            sessions = self.agent.sessions.list()
            if not sessions:
                self.append_chat_message("system", "Belum ada sesi yang disimpan.")
            else:
                lines = ["[bold yellow]SESI YANG DISIMPAN:[/bold yellow]"]
                for s in sessions:
                    lines.append(f"  - [cyan]{s['id']}[/cyan] [bold]{s['name']}[/bold] ({s['messages']} pesan)")
                self.append_chat_message("system", "\n".join(lines))
        else:
            self.append_chat_message("system", f"[red]Perintah tidak dikenal: {cmd}[/red]")

    def rebuild_chat_history(self) -> None:
        chat_area = self.query_one("#chat-area")
        for child in list(chat_area.children):
            child.remove()

        # Re-add pesan dari history (skip system prompt index 0)
        for msg in self.agent.context.messages[1:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                self.query_one("#chat-area").mount(MessageWidget(role, content))
        self.scroll_chat_to_end()


def run_tui(agent: Agent, cfg: Config) -> None:
    """Fungsi runner untuk meluncurkan TUI."""
    app = AutokerenTUI(agent, cfg)
    try:
        app.run()
    except KeyboardInterrupt:
        pass

