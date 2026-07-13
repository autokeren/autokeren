"""Slash commands handling engine for autokeren."""
from __future__ import annotations

from typing import Any

from autokeren.config import save_config, MCPServerConfig
from autokeren.mcp import MCPClient, MCPTool


def handle_slash_command_sync(
    cmd_line: str,
    agent: Any,
    cfg: Any,
    mcp_clients: list[Any],
    set_allow_all_fn: Any,
) -> str | None:
    """Proses perintah slash secara sinkron dan kembalikan output teks untuk ditampilkan.
    Mengembalikan None jika perintah bukan perintah konfigurasi sinkron.
    """
    parts = cmd_line.strip().split(" ", 1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/help":
        return (
            "[bold yellow]=== Perintah Slash autokeren ===[/bold yellow]\n\n"
            "[bold cyan]── Model & Bahasa ──[/bold cyan]\n"
            "  /model [name]            : Switch model AI\n"
            "  /lang [code]             : Switch bahasa TUI (id/en/zh/ja)\n\n"
            "[bold cyan]── MCP & Tools ──[/bold cyan]\n"
            "  /mcp                      : List MCP servers aktif\n"
            "  /mcp show <name>          : Tampilkan tools dari suatu MCP server\n"
            "  /mcp add <name> <cmd>     : Tambah MCP server baru\n\n"
            "[bold cyan]── Config & Settings ──[/bold cyan]\n"
            "  /config                   : Lihat setting aktif\n"
            "  /config git-commit on|off : Toggle auto git commit\n"
            "  /config cf-verify on|off  : Toggle auto verify setelah deploy\n"
            "  /local [url]              : Set/lihat local LLM endpoint (Ollama)\n"
            "  /approval on|off          : Set approval mode untuk tool\n\n"
            "[bold cyan]── Session & Memory ──[/bold cyan]\n"
            "  /memory                   : Tampilkan project memory\n"
            "  /sessions                 : List saved sessions\n"
            "  /save [name]               : Simpan session saat ini\n"
            "  /resume <id|name>          : Resume session\n"
            "  /reset                    : Reset percakapan\n"
            "  /compact                  : Kompres context history\n"
            "\n"
            "[bold cyan]── FDDM Memory ──[/bold cyan]\n"
            "  /fddm emit <type> <text>  : Simpan memori ke FDDM\n"
            "  /fddm sniff <query>       : Cari memori relevan\n"
            "  /fddm stats               : Statistik FDDM\n"
            "  /fddm decay               : Jalankan pemudaran memori"
        )

    elif cmd == "/config":
        if not arg:
            git_status = "ON" if cfg.autokeren.git_auto_commit.enabled else "OFF"
            cf_status = "ON" if cfg.autokeren.cf_verify.enabled else "OFF"
            local_url = cfg.auth.local_endpoint
            return (
                f"[bold yellow]⚙️ CONFIG AKTIF autokeren:[/bold yellow]\n"
                f"  • Git Auto-Commit : [bold]{git_status}[/bold]\n"
                f"  • CF Auto-Verify  : [bold]{cf_status}[/bold]\n"
                f"  • Local Endpoint  : [cyan]{local_url}[/cyan]"
            )

        subparts = arg.split(" ", 1)
        subopt = subparts[0].lower()
        subval = subparts[1].strip().lower() if len(subparts) > 1 else ""

        if subopt == "git-commit":
            if subval in ("on", "true", "1"):
                cfg.autokeren.git_auto_commit.enabled = True
                agent._git_auto_commit_enabled = True
                save_config(cfg)
                return "[green]✅ Git Auto-Commit diaktifkan (ON).[/green]"
            elif subval in ("off", "false", "0"):
                cfg.autokeren.git_auto_commit.enabled = False
                agent._git_auto_commit_enabled = False
                save_config(cfg)
                return "[yellow]⚠️ Git Auto-Commit dinonaktifkan (OFF).[/yellow]"
            else:
                return "[red]Gunakan: /config git-commit on|off[/red]"
        elif subopt == "cf-verify":
            if subval in ("on", "true", "1"):
                cfg.autokeren.cf_verify.enabled = True
                save_config(cfg)
                return "[green]✅ CF Auto-Verify diaktifkan (ON).[/green]"
            elif subval in ("off", "false", "0"):
                cfg.autokeren.cf_verify.enabled = False
                save_config(cfg)
                return "[yellow]⚠️ CF Auto-Verify dinonaktifkan (OFF).[/yellow]"
            else:
                return "[red]Gunakan: /config cf-verify on|off[/red]"
        else:
            return f"[red]Setting tidak dikenal: {subopt}[/red]"

    elif cmd == "/local":
        if not arg:
            return f"Local LLM Endpoint saat ini: [cyan]{cfg.auth.local_endpoint}[/cyan]"
        cfg.auth.local_endpoint = arg
        save_config(cfg)
        return f"[green]✅ Local LLM Endpoint diubah ke: {arg}[/green]"

    elif cmd == "/approval":
        if not arg:
            return "[red]Gunakan: /approval on|off|ask[/red]"
        val = arg.lower()
        if val in ("off", "allow_all", "a", "false", "0"):
            set_allow_all_fn(True)
            return "[green]✅ Approval Mode dinonaktifkan (Semua tool otomatis diizinkan).[/green]"
        elif val in ("on", "ask", "true", "1"):
            set_allow_all_fn(False)
            return "[yellow]⚠️ Approval Mode diaktifkan (Setiap eksekusi tool butuh konfirmasi).[/yellow]"
        else:
            return "[red]Gunakan: /approval on|off|ask[/red]"

    elif cmd == "/mcp":
        if not arg or arg == "list":
            if not mcp_clients:
                return "[dim]Tidak ada MCP server aktif.[/dim]"
            lines = ["[bold green]⚡ MCP Servers Aktif:[/bold green]"]
            for client in mcp_clients:
                status = "🟢" if client.is_alive() else "🔴"
                tc = len(client.tools()) if client.is_alive() else 0
                lines.append(f"  {status} [bold]{client.name}[/bold] ({tc} tools)")
            return "\n".join(lines)

        subparts = arg.split(" ", 1)
        subcmd = subparts[0].lower()
        subarg = subparts[1].strip() if len(subparts) > 1 else ""

        if subcmd == "show":
            if not subarg:
                return "[red]Gunakan: /mcp show <nama_server>[/red]"
            client = next((c for c in mcp_clients if c.name.lower() == subarg.lower()), None)
            if not client:
                return f"[red]MCP server '{subarg}' tidak ditemukan atau tidak aktif.[/red]"
            try:
                tools = client.tools()
                lines = [f"[bold green]🔧 Tools di server '{client.name}':[/bold green]"]
                for t in tools:
                    lines.append(f"  • [cyan]{t['name']}[/cyan]: {t.get('description', '')[:80]}")
                return "\n".join(lines)
            except Exception as e:
                return f"[red]Gagal membaca tools: {e}[/red]"

        elif subcmd == "add":
            if not subarg or " " not in subarg:
                return "[red]Gunakan: /mcp add <nama_server> <command>[/red]"
            name, cmd_raw = subarg.split(" ", 1)
            command = cmd_raw.split()
            try:
                # Simpan ke config.yaml
                new_srv = MCPServerConfig(name=name, command=command)
                cfg.mcp_servers.append(new_srv)
                save_config(cfg)

                # Start client
                client = MCPClient(name=name, command=command)
                client.start()
                mcp_clients.append(client)

                # Daftarkan tools ke registry
                for tool_schema in client.tools():
                    agent.registry.register(MCPTool(client, tool_schema))

                import autokeren.cli as _cli
                if client not in _cli._mcp_clients:
                    _cli._mcp_clients.append(client)

                return f"[green]✅ MCP Server '{name}' aktif — {len(client.tools())} tools terdaftar.[/green]"
            except Exception as exc:
                return f"[red]Gagal memulai MCP Server: {exc}[/red]"
        else:
            return f"[red]Sub-command MCP tidak dikenal: {subcmd}[/red]"

    elif cmd == "/fddm":
        from autokeren.tools.fddm import FDDMTool

        tool = FDDMTool()
        if not arg:
            return (
                "[bold yellow]🐜 FDDM — Feromon Digital Distributed Memory[/bold yellow]\n\n"
                "  /fddm emit <type> <text>  : Simpan memori (type: error/decision/document/observation)\n"
                "  /fddm sniff <query>       : Cari memori relevan\n"
                "  /fddm stats               : Statistik memori\n"
                "  /fddm decay               : Jalankan pemudaran\n"
                "  /fddm trust <emitter> <success|fail> : Lapor kepercayaan emitter"
            )

        subparts = arg.split(" ", 1)
        subcmd = subparts[0].lower()
        subarg = subparts[1].strip() if len(subparts) > 1 else ""

        if subcmd == "emit":
            if not subarg:
                return "[red]Gunakan: /fddm emit <type> <text>[/red]"
            emit_parts = subarg.split(" ", 1)
            emit_type = emit_parts[0].lower()
            emit_text = emit_parts[1].strip() if len(emit_parts) > 1 else ""
            if emit_type not in ("error", "decision", "document", "conversation", "artifact", "observation"):
                return f"[red]Tipe tidak valid: {emit_type}. Pilih: error/decision/document/conversation/artifact/observation[/red]"
            if not emit_text:
                return "[red]Text tidak boleh kosong. Gunakan: /fddm emit <type> <text>[/red]"
            result = tool.run(action="emit", type=emit_type, text=emit_text, emitter_id="autokeren_user")
            if result.ok and isinstance(result.output, dict):
                return f"[green]✅ Scent di-emmit ke FDDM[/green]\n[dim]ID: {result.output.get('scent_id', '?')} | Dim: {result.output.get('dimensions', '?')}[/dim]"
            return f"[red]{result.error}[/red]"

        elif subcmd == "sniff":
            if not subarg:
                return "[red]Gunakan: /fddm sniff <query>[/red]"
            result = tool.run(action="sniff", text=subarg, top_k=5, radius=0.2)
            if result.ok and isinstance(result.output, list):
                if not result.output:
                    return "[yellow]Tidak ada scent yang cocok.[/yellow]"
                lines = ["[bold green]👃 Hasil Sniff FDDM:[/bold green]"]
                for i, hit in enumerate(result.output, 1):
                    hit_dict: dict[str, Any] = hit if isinstance(hit, dict) else {}
                    lines.append(
                        f"  {i}. [cyan]{hit_dict.get('type', '?')}[/cyan] score={hit_dict.get('score', 0):.3f} sim={hit_dict.get('similarity', 0):.3f}\n"
                        f"     [dim]{str(hit_dict.get('artifact', ''))[:120]}[/dim]"
                    )
                return "\n".join(lines)
            return f"[red]{result.error if not result.ok else 'No results'}[/red]"

        elif subcmd == "stats":
            result = tool.run(action="stats")
            if result.ok and isinstance(result.output, dict):
                s = result.output
                return (
                    f"[bold yellow]📊 FDDM Statistics[/bold yellow]\n"
                    f"  • Active Scents : [bold]{s.get('total_scents', 0)}[/bold]\n"
                    f"  • Archived      : [bold]{s.get('archived', 0)}[/bold]\n"
                    f"  • Emitters      : [bold]{s.get('emitters', 0)}[/bold]"
                )
            return f"[red]{result.error}[/red]"

        elif subcmd == "decay":
            result = tool.run(action="decay")
            if result.ok and isinstance(result.output, dict):
                return f"[green]⏳ Decay selesai: {result.output.get('decayed', 0)} decayed, {result.output.get('archived', 0)} archived[/green]"
            return f"[red]{result.error}[/red]"

        elif subcmd == "trust":
            if not subarg:
                return "[red]Gunakan: /fddm trust <emitter_id> <success|fail>[/red]"
            trust_parts = subarg.split()
            if len(trust_parts) < 2:
                return "[red]Gunakan: /fddm trust <emitter_id> <success|fail>[/red]"
            emitter = trust_parts[0]
            success = trust_parts[1].lower() in ("success", "true", "1", "yes")
            result = tool.run(action="trust", emitter_id=emitter, success=success)
            if result.ok and isinstance(result.output, dict):
                return f"[green]✅ Trust updated: {result.output.get('emitter_id')} = {result.output.get('trust', 0)}[/green]"
            return f"[red]{result.error}[/red]"

        else:
            return f"[red]Sub-command FDDM tidak dikenal: {subcmd}[/red]"

    return None
