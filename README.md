# autokeren

**Cloudflare-first agentic coding CLI untuk developer Indonesia dan global.**

autokeren adalah CLI agentic coding yang dirancang khusus untuk stack Cloudflare-first. Dibangun dengan Python, mendukung multi-model fallback otomatis antara Kimi K2.7-Code dan GLM 5.2, dilengkapi tools bawaan untuk file, shell, git, browser automation (Camofox), serta deploy Cloudflare Pages/Workers, KV, dan D1.

[![CI](https://github.com/autokeren/autokeren/actions/workflows/ci.yml/badge.svg)](https://github.com/autokeren/autokeren/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/autokeren.svg)](https://pypi.org/project/autokeren/)

---

## Fitur Utama

- **Multi-model fallback otomatis** — Kimi K2.7-Code sebagai primary, GLM 5.2 sebagai secondary, dengan retry exponential backoff dan circuit breaker.
- **Streaming output** — respons token-by-token langsung di terminal via HTTP/2 streaming.
- **Permission system** — konfirmasi sebelum menjalankan command berbahaya atau menulis file, dengan allowlist shell.
- **Cross-session memory** — ingatan per-project tersimpan di `~/.config/autokeren/projects/<slug>/memory.md`, dimuat otomatis tiap startup.
- **Session save/resume** — simpan state percakapan, lanjutkan kapan saja dengan `/save` dan `/resume`.
- **Context tracking + /compact** — pantang pemakaian context window; ringkas otomatis atau manual dengan `/compact`.
- **AGENTS.md support** — instruksi per-project untuk AI agent dimuat otomatis ke system prompt.
- **Indonesian localization** — UI teks dalam Bahasa Indonesia, dirancang untuk developer Indonesia.
- **KV/D1 tools** — baca/tulis Cloudflare KV dan jalankan query D1 langsung dari agent.
- **Camofox e2e** — browser automation end-to-end berbasis profile, tanpa setup tambahan.
- **Tmux supervisor** — spawn dan monitor long-running agent yang survive terminal close.
- **CF Pages/Workers deploy** — helper deploy + build (`next-on-pages`) terintegrasi.

## Perbandingan

| Fitur | autokeren | opencode | Claude Code | AGY |
|---|---|---|---|---|
| Open source | Ya (MIT) | Ya | Tidak | Ya |
| Multi-model fallback otomatis | Ya | Manual | Tidak | Tidak |
| Cloudflare Workers AI native | Ya | Tidak | Tidak | Tidak |
| KV / D1 tools | Ya | Tidak | Tidak | Tidak |
| Camofox e2e built-in | Ya | Tidak | Tidak | Tidak |
| Tmux supervisor | Ya | Tidak | Tidak | Tidak |
| Cross-session memory | Ya | Ya | Ya | Tidak |
| Session save/resume | Ya | Ya | Ya | Tidak |
| Context /compact | Ya | Ya | Ya | Tidak |
| Indonesian localization | Ya | Tidak | Tidak | Tidak |
| Bahasa | Python | Go/TS | TS | Python |

## Instalasi

### Dari PyPI

```bash
pip install autokeren
```

### Dari source (untuk development)

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start

Inisialisasi konfigurasi pertama kali:

```bash
autokeren --init
```

Ini membuat `~/.config/autokeren/config.yaml` (atau copy dari `config.example.yaml` dan isi `account_id` serta `api_token` Cloudflare Workers AI).

### Interactive chat

```bash
autokeren
```

### Single prompt

```bash
autokeren "buat file hello.py yang cetak hello world"
```

### Plan mode

```bash
autokeren --plan
```

### Pilih model

```bash
autokeren -m glm "refactor fungsi ini"
autokeren -m kimi "tulis unit test untuk modul tools"
```

### Contoh percakapan

```
> baca pyproject.toml dan tambahkan field authors
> deploy project ini ke Cloudflare Pages
> jalankan pytest dan perbaiki test yang gagal
> simpan preferensi build ini ke memory
```

## Konfigurasi

Konfigurasi disimpan sebagai YAML transparan di `~/.config/autokeren/config.yaml`.

```yaml
cloudflare:
  account_id: ""          # atau set CLOUDFLARE_ACCOUNT_ID
  api_token: ""           # atau set CLOUDFLARE_API_TOKEN
  primary_model: "@cf/moonshotai/kimi-k2.7-code"
  secondary_model: "@cf/zai-org/glm-5.2"
  max_tokens: 4096
  temperature: 0.3
  timeout: 120.0

retry:
  max_retries: 5
  base_delay: 1.0
  max_delay: 60.0
  exponential_base: 2.0
  jitter: true
  circuit_failure_threshold: 5
  circuit_open_seconds: 30

autokeren:
  plan_mode: false
  max_iterations: 25
  shell_timeout: 180
  shell_allowlist: ["node", "npm", "pnpm", "npx", "git", "wrangler", "python3", "pytest"]
  project_root: "."
  context_window: 262144
  compact_tail_turns: 6
  auto_compact: false
  auto_compact_threshold: 0.8

camofox:
  url: "http://localhost:9377"
  default_profile: "pulsa"
  user_id: "ajat"
```

### Environment variables

| Variable | Deskripsi |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID (override config) |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Workers AI API token (override config) |
| `AUTOKEREN_CONFIG_DIR` | Direktori konfigurasi custom (default `~/.config/autokeren`) |

## Commands

Perintah slash di interactive mode:

| Perintah | Deskripsi |
|---|---|
| `/help` | Tampilkan bantuan dan daftar perintah |
| `/q` atau `/quit` | Keluar dari sesi |
| `/status` | Tampilkan status context window, model aktif, dan info sesi |
| `/compact` | Ringkas history percakapan, pertahankan N turn terakhir |
| `/reset` | Reset sesi percakapan saat ini |
| `/memory` | Tampilkan lokasi dan isi memory per-project |
| `/save [nama]` | Simpan sesi saat ini |
| `/resume <nama\|id>` | Lanjutkan sesi tersimpan |
| `/sessions` | Daftar semua sesi tersimpan |

## Commands Reference

| Command | Deskripsi |
|---|---|
| `/help` | Tampilkan daftar perintah yang tersedia |
| `/q` atau `/quit` | Keluar dari sesi |
| `/status` | Tampilkan status: model aktif, pemakaian context, jumlah tool |
| `/compact` | Ringkas history percakapan untuk hemat context window |
| `/reset` | Bersihkan percakapan, mulai dari awal |
| `/memory` | Lihat lokasi file memory dan isinya |
| `/save [nama]` | Simpan sesi saat ini untuk dilanjutkan nanti |
| `/resume <nama\|id>` | Resume sesi yang tersimpan |
| `/sessions` | Daftar semua sesi tersimpan |

## Tools

autokeren membawa tools bawaan berikut. Setiap tool memiliki permission check dan schema function-calling.

| Tool | Deskripsi |
|---|---|
| `read_file` | Baca isi file |
| `write_file` | Tulis file baru atau overwrite |
| `patch_file` | Patch file dengan search-and-replace |
| `list_files` | List file dalam direktori (glob pattern) |
| `run_shell` | Jalankan shell command dengan allowlist + blocklist |
| `search_code` | Cari konten file dengan regex |
| `fetch_url` | Ambil konten URL |
| `git_status` | Status working tree git |
| `git_diff` | Diff git (staged/unstaged) |
| `git_commit` | Commit perubahan |
| `camofox` | Browser automation end-to-end via Camofox |
| `cf_deploy` | Deploy ke Cloudflare Pages/Workers via wrangler |
| `cf_build_next` | Build Next.js dengan next-on-pages |
| `cf_kv` | Baca/tulis Cloudflare KV namespace |
| `cf_d1` | Jalankan query Cloudflare D1 |
| `tmux` | Supervisor long-running task via tmux |
| `todo` | Kelola todo list multi-step |
| `remember` | Simpan info ke cross-session memory |

## Arsitektur

autokeren mengikuti pola agentic loop sederhana: agent membaca input, memanggil model, mengeksekusi tool calls, dan mengembalikan hasil ke model sampai selesai.

```
cli.py ──> agent.py (core loop) ──> models/ (Cloudflare client + router + retry)
                                     tools/ (Tool base + registry + 18 tools)
                                     context.py (session memory + token tracking)
                                     memory.py (cross-session memory)
                                     session.py (save/resume)
                                     ui.py (rich terminal UI)
```

Detail lengkap ada di [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Contributing

Kontribusi sangat diterima. Lihat [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan setup dev environment, code style, dan proses pull request.

## License

MIT — lihat [LICENSE](LICENSE).

## Disclaimer

autokeren adalah proyek independen dan **tidak berafiliasi dengan, diendorsing oleh, atau sponsori oleh Cloudflare, Inc.** "Cloudflare" serta produk terkait adalah merek dagang Cloudflare, Inc. autokeren menggunakan infrastruktur dan API publik Cloudflare (Workers AI, D1, R2, KV, Pages) sebagai layanan pihak ketiga.
