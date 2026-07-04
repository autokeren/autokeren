"""autokeren CLI."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from autokeren import __version__
from autokeren.agent import Agent
from autokeren.config import ensure_config, init_config, load_config, save_config
from autokeren.memory import MemoryManager
from autokeren.tools import (
    CamofoxTool,
    CloudflareBuildTool,
    CloudflareD1Tool,
    CloudflareDeployTool,
    CloudflareKVTool,
    FetchURLTool,
    GitCommitTool,
    GitDiffTool,
    GitStatusTool,
    ListFilesTool,
    PatchFileTool,
    ReadFileTool,
    RememberTool,
    SearchCodeTool,
    ShellTool,
    TodoTool,
    ToolRegistry,
    TmuxTool,
    WriteFileTool,
)
from autokeren.ui import AgentUI

console = Console()


def build_registry(cfg, project_root: Path, memory: MemoryManager) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ReadFileTool(project_root))
    reg.register(WriteFileTool(project_root))
    reg.register(PatchFileTool(project_root))
    reg.register(ListFilesTool(project_root))
    reg.register(ShellTool(project_root, allowlist=cfg.autokeren.shell_allowlist, default_timeout=cfg.autokeren.shell_timeout))
    reg.register(SearchCodeTool(project_root))
    reg.register(FetchURLTool())
    reg.register(GitStatusTool(project_root))
    reg.register(GitDiffTool(project_root))
    reg.register(GitCommitTool(project_root))
    reg.register(CamofoxTool(cfg))
    reg.register(CloudflareDeployTool(project_root))
    reg.register(CloudflareBuildTool(project_root))
    reg.register(CloudflareKVTool(cfg))
    reg.register(CloudflareD1Tool(cfg))
    reg.register(TmuxTool(project_root))
    reg.register(TodoTool())
    reg.register(RememberTool(memory))
    return reg


def chat_loop(agent: Agent, cfg, ui: AgentUI):
    ui.show_banner(__version__)
    if not cfg.cloudflare.account_id or not cfg.cloudflare.api_token:
        console.print("[yellow]Warning: Cloudflare account_id/api_token belum diisi. Jalankan autokeren --init.[/yellow]")
    if agent.memory.exists():
        console.print(f"[dim]Memory: {agent.memory.line_count()} baris[/dim]")
    sessions = agent.sessions.list()
    if sessions:
        console.print(f"[dim]Saved sessions: {len(sessions)} (ketik /sessions untuk lihat)[/dim]")
    console.print("[dim]Ketik /help untuk bantuan, atau langsung tanya apa saja.[/dim]\n")

    _last_ctrl_c: float = 0

    while True:
        ui.show_status_bar(agent.status_bar_info())
        try:
            user_input = Prompt.ask("[bold blue]kamu[/bold blue]").strip()
        except EOFError:
            console.print("\nSampai jumpa!")
            break
        except KeyboardInterrupt:
            now = time.time()
            if now - _last_ctrl_c < 3:
                console.print("\n[yellow]Keluar.[/yellow]")
                break
            _last_ctrl_c = now
            console.print("\n[yellow]Ctrl+C lagi dalam 3 detik untuk keluar.[/yellow]")
            continue

        if not user_input:
            continue
        if user_input in ("/quit", "/q"):
            break
        if user_input == "/help":
            console.print("Perintah: /q /status /model /compact /reset /memory /permissions /save /resume /sessions")
            continue
        if user_input == "/model" or user_input.startswith("/model "):
            arg = user_input[6:].strip()
            models = agent.router.model_aliases()
            if not arg:
                console.print("[bold]Model tersedia:[/bold]")
                for m in models:
                    short = m["id"].split("/")[-1] if "/" in m["id"] else m["id"]
                    marker = "[green]● active[/green]" if m["active"] else "[dim]○[/dim]"
                    console.print(f"  {marker}  [cyan]{short}[/cyan]  [dim]{m['id']}[/dim]")
                console.print("[dim]Ketik /model <nama> untuk switch[/dim]")
            else:
                target = None
                for m in models:
                    short = m["id"].split("/")[-1] if "/" in m["id"] else m["id"]
                    if arg.lower() in short.lower() or arg.lower() in m["id"].lower():
                        target = m["id"]
                        break
                if target:
                    agent.router.set_primary(target)
                    short = target.split("/")[-1] if "/" in target else target
                    console.print(f"[green]Model aktif: {short}[/green]")
                else:
                    console.print(f"[red]Model '{arg}' tidak ditemukan.[/red]")
            continue
        if user_input == "/status":
            console.print_json(json.dumps(agent.status()))
            ui.show_context_status(agent.context_info())
            continue
        if user_input == "/compact":
            console.print("[dim]mengompak context…[/dim]")
            try:
                msg = agent.compact()
                console.print(f"[green]{msg}[/green]")
                ui.show_context_status(agent.context_info())
            except Exception as e:
                console.print(f"[red]Compact gagal:[/red] {e}")
            continue
        if user_input == "/reset":
            agent.reset()
            ui.reset_permissions()
            console.print("Sesi direset. Permission juga direset.")
            continue
        if user_input == "/permissions":
            ps = ui.permission_status()
            if ps["allow_all"]:
                console.print("[green]Semua tool diizinkan untuk session ini.[/green]")
            elif ps["allowed_tools"]:
                console.print(f"[green]Tool diizinkan:[/green] {', '.join(ps['allowed_tools'])}")
            else:
                console.print("[dim]Belum ada tool yang diizinkan. Akan tanya saat tool destruktif dipanggil.[/dim]")
            continue
        if user_input == "/memory":
            mem = agent.memory.load()
            if mem:
                console.print(Panel(mem, title=f"[bold]memory[/bold] ({agent.memory.line_count()} baris)", border_style="magenta"))
                console.print(f"[dim]File: {agent.memory.get_path()}[/dim]")
            else:
                console.print("[dim]Memory kosong. Agent akan simpan otomatis via tool remember.[/dim]")
            continue
        if user_input.startswith("/save"):
            name = user_input[5:].strip() or f"session-{len(agent.sessions.list()) + 1}"
            try:
                sid = agent.save_session(name)
                console.print(f"[green]Session '{name}' disimpan. ID: {sid}[/green]")
            except Exception as e:
                console.print(f"[red]Save gagal:[/red] {e}")
            continue
        if user_input.startswith("/resume"):
            identifier = user_input[7:].strip()
            if not identifier:
                console.print("[yellow]Pakai: /resume <nama|id>[/yellow]")
                continue
            try:
                msg = agent.resume_session(identifier)
                console.print(f"[green]{msg}[/green]")
                ui.show_context_status(agent.context_info())
            except Exception as e:
                console.print(f"[red]Resume gagal:[/red] {e}")
            continue
        if user_input == "/sessions":
            sessions = agent.sessions.list()
            if not sessions:
                console.print("[dim]Belum ada saved session.[/dim]")
            else:
                lines = []
                for s in sessions:
                    lines.append(f"  [cyan]{s['id']}[/cyan]  [bold]{s['name']}[/bold]  [dim]{s['timestamp'][:19]}  {s['messages']} pesan[/dim]")
                console.print(Panel("\n".join(lines), title=f"[bold]sessions[/bold] ({len(sessions)})", border_style="cyan"))
                console.print("[dim]Ketik /resume <nama|id> untuk resume[/dim]")
            continue

        try:
            resp = agent.run(user_input)
            ui.show_response(resp)

            # Plan mode loop
            while cfg.autokeren.plan_mode and not agent.plan_approved:
                approved = Confirm.ask("Setujui rencana ini?")
                if approved:
                    agent.approve_plan()
                    resp = agent.run("")
                    ui.show_response(resp)
                else:
                    agent.context.add_user("User menolak rencana. Tanya apa yang perlu diubah.")
                    resp = agent.run("")
                    ui.show_response(resp)

            # Context status after each response
            info = agent.context_info()
            ui.show_context_status(info)

            # Auto-compact suggestion
            if info["pct"] >= cfg.autokeren.auto_compact_threshold * 100:
                console.print(f"[yellow]⚠ Context sudah {info['pct']:.0f}%. Ketik /compact untuk meringkas.[/yellow]")
        except KeyboardInterrupt:
            now = time.time()
            if now - _last_ctrl_c < 3:
                console.print("\n[yellow]Keluar.[/yellow]")
                break
            _last_ctrl_c = now
            console.print("\n[yellow]Dibatalkan. Ctrl+C lagi dalam 3 detik untuk keluar.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
        finally:
            ui.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(prog="autokeren", description="Cloudflare-first agentic coding CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--init", action="store_true", help="Create or overwrite config interactively")
    parser.add_argument("--config", help="Path to config YAML")
    parser.add_argument("--plan", action="store_true", help="Start in plan mode")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--workspace", "-w", dest="project_root", help="Alias for --project-root")
    parser.add_argument("--model", "-m", choices=["glm", "kimi"], help="Override primary model alias for this run")
    parser.add_argument("prompt", nargs="?", help="Single prompt to run non-interactively")
    args = parser.parse_args()

    if args.init:
        cfg = init_config(interactive=True)
        console.print(f"Config saved to {save_config(cfg)}")
        return 0

    cfg = load_config(Path(args.config)) if args.config else ensure_config()
    if args.plan:
        cfg.autokeren.plan_mode = True
    if args.model == "glm":
        cfg.cloudflare.primary_model = "@cf/zai-org/glm-5.2"
    elif args.model == "kimi":
        cfg.cloudflare.primary_model = "@cf/moonshotai/kimi-k2.7-code"

    project_root = Path(args.project_root).expanduser().resolve()
    memory = MemoryManager(str(project_root))
    reg = build_registry(cfg, project_root, memory)
    agent = Agent(cfg, reg, str(project_root), memory=memory)

    ui = AgentUI(console)
    agent.on_model_start = ui.on_model_start
    agent.on_model_end = ui.on_model_end
    agent.on_tool_start = ui.on_tool_start
    agent.on_tool_end = ui.on_tool_end
    agent.on_chunk = ui.on_chunk
    agent.permission_callback = ui.confirm_permission

    if args.prompt:
        ui.show_banner(__version__)
        try:
            resp = agent.run(args.prompt)
            ui.show_response(resp)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
        finally:
            ui.cleanup()
        return 0

    chat_loop(agent, cfg, ui)
    return 0


if __name__ == "__main__":
    sys.exit(main())
