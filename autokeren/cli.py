"""autokeren CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from autokeren import __version__
from autokeren.agent import Agent
from autokeren.config import ensure_config, init_config, load_config, save_config
from autokeren.tools import (
    CamofoxTool,
    CloudflareBuildTool,
    CloudflareDeployTool,
    FetchURLTool,
    GitCommitTool,
    GitDiffTool,
    GitStatusTool,
    ListFilesTool,
    PatchFileTool,
    ReadFileTool,
    SearchCodeTool,
    ShellTool,
    TodoTool,
    ToolRegistry,
    TmuxTool,
    WriteFileTool,
)
from autokeren.ui import AgentUI

console = Console()


def build_registry(cfg, project_root: Path) -> ToolRegistry:
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
    reg.register(TmuxTool(project_root))
    reg.register(TodoTool())
    return reg


def chat_loop(agent: Agent, cfg, ui: AgentUI):
    ui.show_banner(__version__)
    if not cfg.cloudflare.account_id or not cfg.cloudflare.api_token:
        console.print("[yellow]Warning: Cloudflare account_id/api_token belum diisi. Jalankan autokeren --init.[/yellow]")
    console.print("[dim]Ketik /help untuk bantuan, atau langsung tanya apa saja.[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("\n[bold blue]kamu[/bold blue]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nSampai jumpa!")
            break

        if not user_input:
            continue
        if user_input in ("/quit", "/q"):
            break
        if user_input == "/help":
            console.print("Perintah: /q (keluar), /status, /compact, /reset")
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
            console.print("Sesi direset.")
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
    reg = build_registry(cfg, project_root)
    agent = Agent(cfg, reg, str(project_root))

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
