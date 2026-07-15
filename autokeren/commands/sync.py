"""Sync slash commands — config, mcp, approval, fddm. Returns text, no side-effects on agent loop."""
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
            "  /compact                  : Kompres context history\n\n"
            "[bold cyan]── FDDM Memory ──[/bold cyan]\n"
            "  /config fddm on|off       : Aktifkan/matikan FDDM\n"
            "  /fddm emit <type> <text>  : Simpan memori ke FDDM\n"
            "  /fddm sniff <query>       : Cari memori relevan\n"
            "  /fddm stats               : Statistik FDDM\n"
            "  /fddm decay               : Jalankan pemudaran memori"
        )

    elif cmd == "/config":
        if not arg:
            git_status = "ON" if cfg.autokeren.git_auto_commit.enabled else "OFF"
            cf_status = "ON" if cfg.autokeren.cf_verify.enabled else "OFF"
            fddm_status = "ON" if cfg.autokeren.fddm.enabled else "OFF"
            local_url = cfg.auth.local_endpoint
            return (
                f"[bold yellow]⚙️ CONFIG AKTIF autokeren:[/bold yellow]\n"
                f"  • Git Auto-Commit : [bold]{git_status}[/bold]\n"
                f"  • CF Auto-Verify  : [bold]{cf_status}[/bold]\n"
                f"  • FDDM Memory     : [bold]{fddm_status}[/bold]\n"
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
        elif subopt == "fddm":
            if subval in ("on", "true", "1"):
                cfg.autokeren.fddm.enabled = True
                save_config(cfg)
                return (
                    "[green]✅ FDDM diaktifkan (ON).[/green]\n"
                    "[dim]Pastikan fddm.url sudah diisi di config.yaml.[/dim]"
                )
            elif subval in ("off", "false", "0"):
                cfg.autokeren.fddm.enabled = False
                save_config(cfg)
                return "[yellow]⚠️ FDDM dinonaktifkan (OFF).[/yellow]"
            else:
                return "[red]Gunakan: /config fddm on|off[/red]"
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
                lines = [f"[bold green]🛠 Tools di server '{client.name}':[/bold green]"]
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
                new_srv = MCPServerConfig(name=name, command=command)
                cfg.mcp_servers.append(new_srv)
                save_config(cfg)

                client = MCPClient(name=name, command=command)
                client.start()
                mcp_clients.append(client)

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

        if not cfg.autokeren.fddm.enabled or not cfg.autokeren.fddm.url:
            return (
                "[yellow]⚠️ FDDM belum dikonfigurasi.[/yellow]\n"
                "Aktifkan dengan: /config fddm on\n"
                "Pastikan fddm.url dan fddm.api_key diisi di config.yaml."
            )

        fddm_tool = FDDMTool(cfg.autokeren.fddm.url, cfg.autokeren.fddm.api_key)
        subparts = arg.split(" ", 1)
        subcmd = subparts[0].lower()
        subarg = subparts[1].strip() if len(subparts) > 1 else ""

        if subcmd == "emit":
            if not subarg:
                return "[red]Gunakan: /fddm emit <type> <text>[/red]"
            type_text = subarg.split(" ", 1)
            emit_type = type_text[0] if len(type_text) > 1 else "note"
            emit_text = type_text[1] if len(type_text) > 1 else type_text[0]
            result = fddm_tool.run(action="emit", type_=emit_type, text=emit_text)
            output = result.output or result.error or "Emit selesai."
            return str(output)

        elif subcmd == "sniff":
            if not subarg:
                return "[red]Gunakan: /fddm sniff <query>[/red]"
            result = fddm_tool.run(action="sniff", text=subarg)
            output = result.output or result.error or "Tidak ada hasil."
            return str(output)

        elif subcmd == "stats":
            result = fddm_tool.run(action="stats")
            output = result.output or result.error or "Tidak ada statistik."
            return str(output)

        elif subcmd == "decay":
            result = fddm_tool.run(action="decay")
            output = result.output or result.error or "Decay selesai."
            return str(output)

        else:
            return "[red]Gunakan: /fddm emit <type> <text> | sniff <query> | stats | decay[/red]"

    return None
# ak:7d225fd2bc4c7d72
