"""autokeren CLI."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from autokeren import __version__
from autokeren.agent import Agent
from autokeren.config import ensure_config, init_config, load_config, save_config
from autokeren.genome import GuardianChecker
from autokeren.memory import MemoryManager
from autokeren.tools import (
    CamofoxTool,
    CloudflareBuildTool,
    CloudflareD1Tool,
    CloudflareDeployTool,
    CloudflareKVTool,
    CreateProjectTool,
    DeployProjectTool,
    FetchURLTool,
    GenomeTool,
    GitBranchTool,
    GitCommitTool,
    GitDiffTool,
    GitLogTool,
    GitStatusTool,
    ListFilesTool,
    ListProjectsTool,
    PatchFileTool,
    ReadFileTool,
    RememberTool,
    ResearchTool,
    ReviewTool,
    RewindTool,
    SearchCodeTool,
    ShellTool,
    SpawnAgentTool,
    TodoTool,
    ToolRegistry,
    TmuxTool,
    WriteFileTool,
)
from autokeren.ui import AK_THEME, AgentUI
from autokeren.mcp import MCPClient, MCPTool

console = Console(theme=AK_THEME)


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
    reg.register(GitLogTool(project_root))
    reg.register(GitBranchTool(project_root))
    reg.register(CamofoxTool(cfg))
    reg.register(CloudflareDeployTool(project_root))
    reg.register(CloudflareBuildTool(project_root))
    reg.register(CloudflareKVTool(cfg))
    reg.register(CloudflareD1Tool(cfg))
    reg.register(TmuxTool(project_root))
    reg.register(TodoTool())
    reg.register(RememberTool(memory))
    reg.register(SpawnAgentTool(cfg, str(project_root), memory))
    if cfg.auth.mode == "platform":
        reg.register(CreateProjectTool(cfg))
        reg.register(DeployProjectTool(cfg))
        reg.register(ListProjectsTool(cfg))
    return reg


_mcp_clients: list[MCPClient] = []


def load_mcp_servers(cfg, registry: ToolRegistry) -> None:
    """Start semua MCP servers yang dikonfigurasi dan daftarkan tool-nya."""
    global _mcp_clients
    for srv_cfg in cfg.mcp_servers:
        if not srv_cfg.enabled:
            continue
        try:
            client = MCPClient(name=srv_cfg.name, command=srv_cfg.command, env=srv_cfg.env or {})
            client.start()
            _mcp_clients.append(client)
            for tool_schema in client.tools():
                registry.register(MCPTool(client, tool_schema))
            console.print(f"[green]✓ MCP server '[bold]{srv_cfg.name}[/bold]' terhubung — {len(client.tools())} tools.[/green]")
        except Exception as exc:
            console.print(f"[yellow]⚠ MCP server '[bold]{srv_cfg.name}[/bold]' gagal dimulai: {exc}[/yellow]")


def stop_mcp_servers() -> None:
    """Hentikan semua MCP server saat program keluar."""
    for client in _mcp_clients:
        try:
            client.stop()
        except Exception:
            pass
    _mcp_clients.clear()


def _read_input(console: Console) -> str:
    """Read user input. Simple Prompt.ask, no paste detection."""
    return Prompt.ask("[bold blue]kamu[/bold blue]").strip()


def chat_loop(agent: Agent, cfg, ui: AgentUI):
    ui.show_banner(__version__)
    if cfg.auth.mode == "platform" and not cfg.auth.api_key:
        console.print("[yellow]Warning: API key belum diisi. Jalankan autokeren --login.[/yellow]")
    elif cfg.auth.mode == "direct" and (not cfg.cloudflare.account_id or not cfg.cloudflare.api_token):
        console.print("[yellow]Warning: Cloudflare account_id/api_token belum diisi. Jalankan autokeren --init.[/yellow]")
    elif cfg.auth.mode == "aistudio" and not cfg.auth.gemini_api_key:
        console.print("[yellow]Warning: Gemini API key belum diisi. Set GEMINI_API_KEY env var atau update config.yaml.[/yellow]")
    else:
        console.print(f"[dim]Auth: {cfg.auth.mode}[/dim]")
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
            user_input = _read_input(console)
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
            console.print("Perintah: /q /status /model /compact /deploy /rewind /genome /loop /review /security /spec /ghost /research /reset /debug /memory /permissions /save /resume /sessions /diagram")
            continue
        if user_input == "/model" or user_input.startswith("/model "):
            arg = user_input[6:].strip()
            if arg:
                if cfg.auth.mode in ("antigravity", "aistudio"):
                    resolved = arg
                else:
                    from autokeren.models.cloudflare import resolve_model_id
                    resolved = resolve_model_id(arg, getattr(agent.router.models[0], "auth_mode", "direct"))
                if agent.router.switch_model(resolved):
                    ui.set_model_name(agent.router.current_model_id())
                    console.print(f"[green]Model aktif: {arg}[/green]")
                else:
                    console.print(f"[red]Model '{arg}' tidak ditemukan.[/red]")
            else:
                if cfg.auth.mode == "antigravity":
                    from autokeren.models.antigravity import fetch_antigravity_models
                    all_models = fetch_antigravity_models()
                elif cfg.auth.mode == "aistudio":
                    from autokeren.models.aistudio import fetch_aistudio_models
                    all_models = fetch_aistudio_models(cfg)
                else:
                    from autokeren.models.cloudflare import fetch_available_models
                    all_models = fetch_available_models(cfg)
                
                from autokeren.selector import select_option
                current = agent.router.current_model_id()
                for m in all_models:
                    m["active"] = m["id"] == current

                idx = select_option(all_models, title="Pilih Model", console=console)
                if idx is not None:
                    chosen = all_models[idx]["id"]
                    if cfg.auth.mode in ("antigravity", "aistudio"):
                        resolved = chosen
                    else:
                        from autokeren.models.cloudflare import resolve_model_id
                        resolved = resolve_model_id(chosen, getattr(agent.router.models[0], "auth_mode", "direct"))
                    agent.router.switch_model(resolved)
                    console.print(f"[green]Model aktif: {all_models[idx]['name']} ({chosen})[/green]")
                else:
                    console.print("[dim]Dibatalkan.[/dim]")
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
        if user_input == "/debug":
            import os
            import logging
            current_debug = os.environ.get("AUTOKEREN_DEBUG") == "1"
            if current_debug:
                os.environ.pop("AUTOKEREN_DEBUG", None)
                logging.getLogger().setLevel(logging.WARNING)
                console.print("[blue]Mode Debug NON-AKTIF. Traceback internal tidak akan ditampilkan secara detail.[/blue]")
            else:
                os.environ["AUTOKEREN_DEBUG"] = "1"
                logging.basicConfig(filename="autokeren-debug.log", level=logging.DEBUG, force=True)
                logging.debug("Debug mode activated in CLI.")
                console.print("[blue]Mode Debug AKTIF. Traceback internal akan ditampilkan. Detail debug dicatat di autokeren-debug.log.[/blue]")
            continue
        if user_input.startswith("/rewind"):
            if not agent.checkpoints:
                console.print("[yellow]Time-Travel tidak diaktifkan.[/yellow]")
                continue
            arg = user_input[7:].strip()
            if arg == "list":
                cps = agent.checkpoints.list_checkpoints()
                if not cps:
                    console.print("[dim]Tidak ada checkpoint.[/dim]")
                else:
                    for cp in cps:
                        import datetime
                        ts = datetime.datetime.fromtimestamp(cp["timestamp"]).strftime("%H:%M:%S")
                        path = cp["args"].get("path", cp["args"].get("query", ""))
                        console.print(f"  #{cp['id']} [{ts}] {cp['tool']}({path}) — {cp['changes']} changes {'✗' if not cp['ok'] else '✓'}")
                continue
            steps = int(arg) if arg.isdigit() else 1
            if steps < 1:
                steps = 1
            total = agent.checkpoints.count()
            if total == 0:
                console.print("[dim]Tidak ada checkpoint untuk di-rewind.[/dim]")
                continue
            console.print(f"[dim]Rewinding {min(steps, total)} tool call…[/dim]")
            undone = agent.checkpoints.rewind(steps)
            if undone:
                for entry in undone:
                    path = entry.tool_args.get("path", entry.tool_args.get("query", ""))
                    n = len(entry.file_changes)
                    console.print(f"  ⏪ #{entry.id} {entry.tool_name}({path}) — {n} file di-revert")
                console.print(f"[green]Rewind selesai. {agent.checkpoints.count()} checkpoint tersisa.[/green]")
            else:
                console.print("[yellow]Tidak ada yang di-rewind.[/yellow]")
            continue
        if user_input == "/diagram":
            ui.render_last_diagram()
            continue
        if user_input.startswith("/security"):
            if not agent.security_scanner:
                console.print("[yellow]Vibe-Security tidak diaktifkan.[/yellow]")
                continue
            arg = user_input[9:].strip()
            if arg:
                findings = agent.security_scanner.scan_file(arg)
            else:
                findings = []
                for p in Path(agent.project_root).rglob("*"):
                    if p.is_file() and p.suffix in (".py", ".js", ".ts", ".jsx", ".tsx"):
                        rel = str(p.relative_to(agent.project_root))
                        if ".ak-" in rel or "node_modules" in rel or ".venv" in rel:
                            continue
                        findings.extend(agent.security_scanner.scan_file(str(p)))
            console.print(agent.security_scanner.format_findings(findings))
            continue
        if user_input.startswith("/review"):
            from autokeren.tools.review import collect_git_diff
            arg = user_input[7:].strip()
            diff = collect_git_diff(agent.project_root, staged=(arg == "staged"))
            if not diff:
                console.print("[dim]Tidak ada diff untuk di-review.[/dim]")
                continue
            coder_model = agent.router.current_model_id()
            from autokeren.review.selector import ReviewerSelector
            from autokeren.review.parser import parse_review_output, format_review_for_agent
            reviewer = ReviewerSelector().select(coder_model)
            console.print(f"[dim]Reviewing dengan model: {reviewer}…[/dim]")
            review_prompt = (
                "Review code diff berikut. Cek: bugs, security, architecture, edge cases.\n\n"
                f"Diff:\n{diff[:8000]}\n\n"
                "Format: SEVERITY/ISSUE/FILE/FIX atau 'NO ISSUES FOUND'"
            )
            try:
                resp = agent.router.complete(
                    [{"role": "user", "content": review_prompt}],
                    max_tokens=2048,
                    temperature=0.0,
                )
                result = parse_review_output(resp.content or "", reviewer)
                console.print(format_review_for_agent(result))
            except Exception as e:
                console.print(f"[red]Review gagal:[/red] {e}")
            continue
        if user_input.startswith("/loop"):
            if not agent.loop_breaker:
                console.print("[yellow]Loop Breaker tidak diaktifkan.[/yellow]")
                continue
            arg = user_input[5:].strip()
            if arg == "reset":
                agent.loop_breaker.reset()
                if agent._pattern_detector:
                    agent._pattern_detector.reset()
                console.print("[green]Loop Breaker di-reset.[/green]")
            elif arg == "status":
                st = agent.loop_breaker.status()
                console.print(f"Total errors tracked: {st['total_errors']}")
                console.print(f"Unique recent: {st['unique_recent']}")
                for h in st["history"]:
                    console.print(f"  {h['tool']} — {h['error']}")
            elif arg == "break":
                agent.router.swap_models()
                agent.loop_breaker.reset()
                console.print("[green]Manual loop break: model di-swap, history di-reset.[/green]")
            else:
                console.print("/loop status | reset | break")
            continue
        if user_input.startswith("/genome"):
            if not agent._genome_scanner:
                console.print("[yellow]Architecture Guardian tidak diaktifkan.[/yellow]")
                continue
            arg = user_input[6:].strip()
            if arg == "rescan":
                agent._genome = agent._genome_scanner.scan()
                agent._guardian_checker = GuardianChecker(agent._genome) if agent._genome else None
                console.print(f"[green]Genome di-rescan. {len(agent._genome.modules)} modules, {len(agent._genome.dependencies)} deps.[/green]")
            elif arg == "check":
                dups = agent._genome.find_duplicate_functions() if agent._genome else {}
                if not dups:
                    console.print("[green]Tidak ada duplicate functions.[/green]")
                else:
                    for name, entries in dups.items():
                        locs = ", ".join(f"{e.module}:{e.file}:{e.line}" for e in entries)
                        console.print(f"  [yellow]{name}[/yellow] — {locs}")
            else:
                g = agent._genome
                if g:
                    console.print(f"[bold]Project Genome[/bold] — {len(g.modules)} modules, {len(g.dependencies)} deps")
                    for mod in g.modules:
                        console.print(f"  [{mod.language}] {mod.name} — {len(mod.functions)} functions")
                    dups = g.find_duplicate_functions()
                    if dups:
                        console.print(f"\n[yellow]⚠ {len(dups)} duplicate functions[/yellow]")
                else:
                    console.print("[dim]Genome kosong.[/dim]")
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
        if user_input.startswith("/spec"):
            from autokeren.spec import SpecPlanner
            if not hasattr(agent, "_spec_planner"):
                agent._spec_planner = SpecPlanner(router=agent.router, num_questions=cfg.autokeren.spec_driven.num_questions)  # type: ignore[attr-defined]
            sp = agent._spec_planner  # type: ignore[attr-defined]
            arg = user_input[5:].strip()
            if not arg:
                console.print("/spec <request> | answer <text> | generate | show | progress")
                continue
            if arg.startswith("answer "):
                text = arg[7:]
                if sp.session:
                    nxt = sp.session.answer(text)
                    if nxt:
                        console.print(f"[cyan]Q{sp.session.current}:[/cyan] {nxt}")
                    else:
                        console.print("[green]Interview selesai. Ketik /spec generate untuk buat plan.[/green]")
                else:
                    console.print("[yellow]Belum ada interview. Ketik /spec <request>.[/yellow]")
            elif arg == "generate":
                plan = sp.generate_plan()
                if plan:
                    plan.save(Path(agent.project_root))
                    console.print("[green]Plan disimpan: plan.md + technical-plan.md[/green]")
                    console.print(f"[dim]{len(plan.steps)} implementation steps[/dim]")
                else:
                    console.print("[yellow]Interview belum selesai.[/yellow]")
            elif arg == "show":
                if sp.plan:
                    console.print(Panel(sp.plan.plan_md[:2000], title="plan.md", border_style="cyan"))
                else:
                    console.print("[dim]Belum ada plan. Ketik /spec generate.[/dim]")
            elif arg == "progress":
                if sp.plan:
                    console.print(f"Progress: {sp.plan.progress:.0f}% ({len(sp.plan.completed_steps)}/{len(sp.plan.steps)} steps)")
                else:
                    console.print("[dim]Belum ada plan.[/dim]")
            else:
                session = sp.start_interview(arg)
                if session.questions:
                    console.print(f"[green]Interview dimulai: {len(session.questions)} pertanyaan.[/green]")
                    console.print(f"[cyan]Q1:[/cyan] {session.questions[0]}")
                    console.print("[dim]Jawab dengan: /spec answer <jawaban>[/dim]")
                else:
                    console.print("[yellow]Gagal generate pertanyaan.[/yellow]")
            continue
        if user_input.startswith("/ghost"):
            from autokeren.ghost import GhostManager
            if not hasattr(agent, "_ghost_manager"):
                gc = cfg.autokeren.ghost_agent
                agent._ghost_manager = GhostManager(  # type: ignore[attr-defined]
                    project_root=agent.project_root,
                    max_agents=gc.max_background,
                    prefix=gc.tmux_prefix,
                )
            gm = agent._ghost_manager  # type: ignore[attr-defined]
            arg = user_input[6:].strip()
            if not arg:
                console.print("/ghost <task> | list | show <id> | kill <id>|all")
                continue
            if arg == "list":
                agents = gm.list_agents()
                if not agents:
                    console.print("[dim]Tidak ada ghost agent.[/dim]")
                else:
                    for a in agents:
                        gm.check_status(a.id)
                        console.print(f"  #{a.id} [{a.status}] {a.task[:60]} ({a.runtime:.0f}s)")
            elif arg.startswith("show "):
                aid = int(arg[5:].strip()) if arg[5:].strip().isdigit() else 0
                output = gm.get_output(aid)
                if output:
                    console.print(Panel(output[-3000:], title=f"Ghost #{aid}", border_style="cyan"))
                else:
                    console.print("[dim]Tidak ada output.[/dim]")
            elif arg.startswith("kill "):
                target = arg[5:].strip()
                if target == "all":
                    for a in gm.list_agents():
                        gm.kill(a.id)
                    console.print("[green]Semua ghost agent di-kill.[/green]")
                elif target.isdigit():
                    gm.kill(int(target))
                    console.print(f"[green]Ghost #{target} di-kill.[/green]")
                else:
                    console.print("[yellow]Pakai: /ghost kill <id>|all[/yellow]")
            else:
                try:
                    info = gm.spawn(arg)
                    console.print(f"[green]👻 Ghost Agent #{info.id} di-spawn: {arg[:60]}[/green]")
                    console.print(f"[dim]Lihat: /ghost show {info.id} | /ghost list[/dim]")
                except Exception as e:
                    console.print(f"[red]Spawn gagal:[/red] {e}")
            continue
        if user_input.startswith("/research"):
            if not cfg.autokeren.research.enabled:
                console.print("[yellow]Research tool tidak diaktifkan.[/yellow]")
                continue
            arg = user_input[9:].strip()
            if not arg:
                console.print("/research <query> | reddit <q> | hn <q> | web <q>")
                continue
            sources: list[str] | None = None
            query = arg
            if arg.startswith("reddit "):
                sources = ["reddit"]
                query = arg[7:]
            elif arg.startswith("hn "):
                sources = ["hackernews"]
                query = arg[3:]
            elif arg.startswith("web "):
                sources = ["web"]
                query = arg[4:]
            rc = cfg.autokeren.research
            tool = ResearchTool(
                router=agent.router,
                max_results=rc.max_results,
                max_depth=rc.max_depth,
                summarize=rc.summarize,
                min_comment_score=rc.min_comment_score,
            )
            console.print(f"[dim]Researching: {query}…[/dim]")
            res = tool.run(query=query, sources=sources, depth=rc.max_depth)
            if res.ok:
                console.print(Panel(res.to_string(), title=f"Research: {query}", border_style="cyan"))
            else:
                console.print(f"[red]Research gagal:[/red] {res.error}")
            continue
        if user_input.startswith("/deploy"):
            arg = user_input[7:].strip()
            if not arg:
                console.print("[yellow]Pakai: /deploy <deskripsi app>[/yellow]")
                console.print("[dim]Contoh: /deploy toko online dengan keranjang dan checkout[/dim]")
                console.print("[dim]AI akan: create_project → write_file → deploy_project → URL live[/dim]")
                continue
            deploy_prompt = (
                f"User minta deploy app ke Cloudflare: {arg}\n\n"
                "LANGKAH WAJIB (jangan skip):\n"
                "1. Panggil create_project(name=\"nama-project-yang-singkat\") untuk provisioning D1+R2+AI.\n"
                "2. Tulis Worker code ke file lokal pakai write_file(path=\"worker.js\", content=\"...\").\n"
                "   - MAX 500 BARIS PER FILE. Kalau app besar, tulis bertahap:\n"
                "     a. write_file untuk base structure (HTML skeleton + API routes + D1 init)\n"
                "     b. patch_file untuk tambah CSS (ganti /* STYLES */ placeholder)\n"
                "     c. patch_file untuk tambah JS (ganti /* SCRIPT */ placeholder)\n"
                "   - Gunakan template literals (backtick) untuk HTML/CSS/JS.\n"
                "   - Responsive, modern, clean. Bukan HTML basic.\n"
                "3. Panggil deploy_project(project_id, file_path=\"worker.js\") untuk deploy.\n"
                "4. Return URL live ke user.\n"
                "JANGAN inline script ke deploy_project. Tulis ke file dulu."
            )
            try:
                resp = agent.run(deploy_prompt)
                ui.show_response(resp)
            except Exception as e:
                console.print(f"[red]Deploy gagal:[/red] {e}")
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


def _try_run_go_tui(args: argparse.Namespace, sys_argv: list[str]) -> bool:
    """Mencoba meluncurkan TUI Go (ak). Mengembalikan False jika harus fallback ke Python TUI."""
    if args.about or args.init or args.login or args.prompt or args.task or args.non_interactive:
        return False

    import os
    import sys
    import shutil
    import subprocess
    from pathlib import Path

    os.environ["AUTOKEREN_PYTHON_PATH"] = sys.executable
    cache_dir = Path.home() / ".cache" / "autokeren" / "bin"
    ak_bin = cache_dir / ("ak.exe" if os.name == "nt" else "ak")

    # Jika biner belum ada, coba compile
    if not ak_bin.exists():
        go_path = shutil.which("go")
        if not go_path:
            return False  # Tidak ada Go compiler, langsung fallback
        
        # Cari source Go di site-packages
        package_dir = Path(__file__).parent
        go_src_dir = package_dir / "go"
        
        # Jika tidak ada source Go di site-packages (misal development mode biasa di repo),
        # coba cari di root direktori repo
        if not go_src_dir.exists():
            go_src_dir = package_dir.parent
            if not (go_src_dir / "main.go").exists():
                return False

        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            # Jalankan go build
            subprocess.run(
                [go_path, "build", "-o", str(ak_bin), "main.go"],
                cwd=str(go_src_dir),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return False  # Gagal kompilasi, fallback

    if ak_bin.exists():
        # Jalankan biner Go. Gunakan os.execvp agar menggantikan proses Python saat ini secara instan
        argv = [str(ak_bin)] + sys_argv[1:]
        try:
            os.execvp(str(ak_bin), argv)
        except Exception:
            return False
            
    return False


def main() -> int:
    parser = argparse.ArgumentParser(prog="autokeren", description="Cloudflare-first agentic coding CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--about", action="store_true", help="Tampilkan info & disclaimer")
    parser.add_argument("--init", action="store_true", help="Create or overwrite config interactively")
    parser.add_argument("--login", action="store_true", help="Login dengan API key dari developers.autokeren.com")
    parser.add_argument("--config", help="Path to config YAML")
    parser.add_argument("--plan", action="store_true", help="Start in plan mode")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--workspace", "-w", dest="project_root", help="Alias for --project-root")
    parser.add_argument("--model", "-m", help="Override primary model (alias atau @cf/... ID)")
    parser.add_argument("--agy", action="store_true", help="Otomatis gunakan Google Antigravity backend")
    parser.add_argument("--aistudio", action="store_true", help="Otomatis gunakan Google AI Studio backend")
    parser.add_argument("--non-interactive", action="store_true", help="Run single task, no REPL (for ghost agent)")
    parser.add_argument("--task", help="Task untuk non-interactive mode")
    parser.add_argument("prompt", nargs="?", help="Single prompt to run non-interactively")
    args = parser.parse_args()
    _try_run_go_tui(args, sys.argv)

    if args.about:
        console.print(f"\n[bold]autokeren[/bold] v{__version__}")
        console.print("Cloudflare-first agentic coding CLI buat developer Indonesia\n")
        console.print("[dim]GitHub:[/dim] https://github.com/autokeren/autokeren")
        console.print("[dim]Platform:[/dim] https://developers.autokeren.com\n")
        console.print("[yellow]Disclaimer:[/yellow]")
        console.print("[dim]autokeren adalah proyek independen dan tidak berafiliasi dengan,")
        console.print("[dim]diendorsing oleh, atau sponsori oleh Cloudflare, Inc.")
        console.print('[dim]"Cloudflare" serta produk terkait adalah merek dagang Cloudflare, Inc.\n')
        return 0

    if args.init:
        cfg = init_config(interactive=True)
        console.print(f"Config saved to {save_config(cfg)}")
        return 0

    if args.login:
        import httpx as _httpx
        console.print("[bold]Login AutoKeren Platform[/bold]")
        console.print("Buka [cyan]https://developers.autokeren.com/dashboard/keys[/cyan] buat API key.")
        console.print("Format: [dim]ak_live_...[/dim]\n")
        api_key = Prompt.ask("API key").strip()
        if not api_key or not api_key.startswith("ak_"):
            console.print("[red]API key tidak valid. Harus diawali 'ak_'[/red]")
            return 1
        console.print("[dim]Memvalidasi API key...[/dim]")
        try:
            r = _httpx.get(
                "https://api.developers.autokeren.com/v1/usage",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                console.print(f"[green]Login berhasil![/green] Tier: {data.get('tier', '?')}")
                cfg = load_config(Path(args.config)) if args.config else ensure_config()
                cfg.auth.mode = "platform"
                cfg.auth.api_key = api_key
                save_config(cfg)
                console.print("[dim]Config saved.[/dim]")
                return 0
            else:
                err = r.json().get("error", {}).get("message", "unknown error")
                console.print(f"[red]Validasi gagal: {err}[/red]")
                return 1
        except Exception as e:
            console.print(f"[red]Connection error: {e}[/red]")
            return 1

    cfg = load_config(Path(args.config)) if args.config else ensure_config()
    if args.agy:
        from autokeren.models.google_auth import verify_or_login
        if not verify_or_login(console):
            return 1
        cfg.auth.mode = "antigravity"
        if not args.model:
            cfg.cloudflare.primary_model = "Gemini 3.5 Flash (Low)"
    elif args.aistudio:
        if not cfg.auth.gemini_api_key:
            console.print("\n[bold yellow]🔑 SETUP GOOGLE AI STUDIO (GEMINI API)[/bold yellow]")
            console.print("API Key tidak ditemukan di config atau env var GEMINI_API_KEY.")
            key = Prompt.ask("Masukkan API Key Google AI Studio Anda").strip()
            if not key:
                console.print("[red]API Key tidak boleh kosong.[/red]")
                return 1
            cfg.auth.gemini_api_key = key
            save_config(cfg)
            console.print("[green]✓ API Key disimpan ke config.yaml![/green]")
        cfg.auth.mode = "aistudio"
        if not args.model:
            cfg.cloudflare.primary_model = "gemini-3.5-flash"
    if args.plan:
        cfg.autokeren.plan_mode = True
    if args.model:
        if cfg.auth.mode in ("antigravity", "aistudio"):
            cfg.cloudflare.primary_model = args.model
        else:
            from autokeren.models.cloudflare import resolve_model_id
            if cfg.auth.mode == "platform":
                cfg.cloudflare.primary_model = resolve_model_id(args.model, "platform")
            else:
                cfg.cloudflare.primary_model = args.model

    project_root = Path(args.project_root).expanduser().resolve()
    memory = MemoryManager(str(project_root))
    reg = build_registry(cfg, project_root, memory)
    load_mcp_servers(cfg, reg)
    agent = Agent(cfg, reg, str(project_root), memory=memory)
    if agent.checkpoints:
        reg.register(RewindTool(agent.checkpoints))
    if agent._genome_scanner and agent._genome:
        reg.register(GenomeTool(agent._genome_scanner, agent._genome))
    if cfg.autokeren.cross_model_review.enabled:
        coder_model = agent.router.current_model_id()
        reg.register(ReviewTool(str(project_root), coder_model=coder_model, router=agent.router))
    if cfg.autokeren.research.enabled:
        rc = cfg.autokeren.research
        reg.register(ResearchTool(
            router=agent.router,
            max_results=rc.max_results,
            max_depth=rc.max_depth,
            summarize=rc.summarize,
            min_comment_score=rc.min_comment_score,
        ))

    ui = AgentUI(console)
    ui.set_model_name(agent.router.current_model_id())
    agent.on_model_start = ui.on_model_start
    agent.on_model_end = ui.on_model_end
    agent.on_tool_start = ui.on_tool_start
    agent.on_tool_end = ui.on_tool_end
    agent.on_tool_output = ui.on_tool_output
    agent.on_chunk = ui.on_chunk
    agent.on_retry = ui.on_retry
    agent.permission_callback = ui.confirm_permission

    if args.prompt or args.task or args.non_interactive:
        ui.mermaid_render = cfg.autokeren.mermaid_render
        ui._allow_all = True
        task = args.task or args.prompt or ""
        if not task:
            console.print("[red]Task kosong. Pakai: autokeren --non-interactive --task \"…\"[/red]")
            return 1
        try:
            resp = agent.run(task)
            ui.show_response(resp)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
        finally:
            ui.cleanup()
        return 0

    from autokeren.tui import run_tui
    try:
        run_tui(agent, cfg)
    finally:
        stop_mcp_servers()
    return 0



if __name__ == "__main__":
    sys.exit(main())
