# AGENTS.md

Panduan untuk AI agent yang bekerja di codebase autokeren.

## Project Overview

autokeren adalah Cloudflare-first agentic coding CLI yang dibangun dengan Python. Agent loop membaca input user, memanggil model Cloudflare Workers AI (Kimi K2.7-Code primary, GLM 5.2 secondary), mengeksekusi tool calls, dan mengembalikan hasil sampai task selesai. Dirancang untuk stack Cloudflare-first dengan tools native untuk KV, D1, Pages/Workers deploy, Camofox e2e, dan tmux supervision.

## Tech Stack

- Python 3.11+
- `httpx` untuk HTTP/2 streaming ke Cloudflare Workers AI
- `rich` untuk terminal UI
- `pydantic` untuk config dan tool schemas
- `pyyaml` / `strictyaml` untuk config YAML
- `pyfiglet` untuk banner
- standard library untuk core tools (pathlib, subprocess, re, hashlib)

## Code Conventions

- **ruff** dengan `line-length = 120`.
- **mypy** strict. Semua code baru harus type-safe.
- **Tidak menambahkan komentar kode** kecuali diminta eksplisit.
- **UI text dalam Bahasa Indonesia** mengikuti konvensi yang sudah ada (pesan error, deskripsi tool, output command).
- Gunakan `from __future__ import annotations` di modul yang memakai type hints modern.
- Konvensi commit: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

## Architecture

Modul inti dan tanggung jawabnya:

| Modul | Tanggung Jawab |
|---|---|
| `agent.py` | Core agentic loop: model call, tool dispatch, iterasi sampai selesai |
| `cli.py` | Entry point, argument parsing, slash-command dispatch, interactive REPL |
| `config.py` | Load + validasi `config.yaml` (pydantic) |
| `context.py` | Session memory: simpan pesan, track token usage vs context window |
| `memory.py` | Cross-session persistent memory per-project (`memory.md`) |
| `session.py` | Save/resume session state ke disk |
| `prompts.py` | Build system prompt (AGENTS.md, memory, tool schemas) |
| `ui.py` | Rich-based terminal UI: panel, streaming, status, banner |
| `utils.py` | Helper: redact, sanitize_filename, is_dangerous_command, human_size |
| `models/` | Cloudflare AI client (`cloudflare.py`), router/fallback (`router.py`), retry + circuit breaker (`retry.py`) |
| `tools/` | `base.py` (Tool ABC + ToolResult + ToolRegistry), 18 tool implementasi |

### Tool System

Setiap tool mewarisi `Tool` (ABC) di `autokeren/tools/base.py` dengan atribut:

- `name`, `description`, `parameters` (JSON schema), `requires_permission`
- `run(**kwargs) -> ToolResult`
- `needs_permission(**kwargs)` dan `permission_desc(**kwargs)` untuk dynamic permission

`ToolRegistry` mengelola registrasi, lookup, schema generation, permission check, dan eksekusi dengan error handling.

### Model Layer

`models/cloudflare.py` — HTTP client ke Workers AI dengan streaming.
`models/router.py` — pilih primary/secondary model, fallback otomatis.
`models/retry.py` — exponential backoff + circuit breaker.

## Testing

- Framework: `pytest`.
- Tests harus cepat dan **tanpa external API call**. Mock network bila perlu.
- Gunakan `tmp_path` + `monkeypatch` untuk isolasi filesystem dan env var (mis. `AUTOKEREN_CONFIG_DIR` untuk `MemoryManager`).
- Sebelum commit, ketiga command berikut harus lolos:

```bash
ruff check .
mypy autokeren
pytest
```

## Aturan Penting

- **Jangan pernah mengubah signature tool yang sudah ada** tanpa pertimbangan matang. Agent dan config bergantung pada `name`, `parameters`, dan `run` kwargs.
- **Selalu jalankan `ruff check .` dan `mypy autokeren`** setelah mengubah code. Keduanya harus bersih.
- Saat menambah tool baru, daftarkan di `autokeren/tools/__init__.py` dan tambahkan ke `__all__`.
- Jangan hardcode credentials. Baca dari config atau env var (`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`).
- Gunakan `redact()` dari `autokeren.utils` saat mencetak token/API key.
