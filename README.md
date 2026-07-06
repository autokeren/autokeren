# autokeren

**Cloudflare-first agentic coding CLI dengan antarmuka TUI interaktif untuk developer Indonesia dan global.**

autokeren adalah CLI agentic coding yang dirancang khusus untuk stack Cloudflare-first. Dibangun dengan Python, autokeren menghadirkan antarmuka **Text User Interface (TUI) interaktif** bergaya Antigravity/AGY yang membagi layar menjadi panel status statis dan area obrolan dinamis, mendukung 7 model AI dengan fallback otomatis, dilengkapi tools bawaan untuk file, shell, git, deploy Cloudflare, serta PaaS built-in.

[![CI](https://github.com/autokeren/autokeren/actions/workflows/ci.yml/badge.svg)](https://github.com/autokeren/autokeren/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/autokeren.svg)](https://pypi.org/project/autokeren/)

![autokeren TUI Screenshot](docs/assets/autogen-ui-preview.jpg)


---

## Fitur Utama

- **7 model AI** — kimi-code, kimi-2.6, glm-5.2, glm-flash, llama-4-scout, gemma-4, nemotron dengan fallback otomatis.
- **PaaS built-in** — deploy aplikasi ke Cloudflare Workers langsung dari terminal, auto D1 + R2 + AI bindings.
- **Streaming output** — respons token-by-token langsung di terminal.
- **Permission system** — konfirmasi sebelum menjalankan command berbahaya atau menulis file.
- **Cross-session memory** — ingatan per-project tersimpan otomatis, dimuat tiap startup.
- **Session save/resume** — simpan state percakapan, lanjutkan kapan saja.
- **Context tracking + /compact** — pantau pemakaian context window, ringkas otomatis atau manual.
- **AGENTS.md support** — instruksi per-project untuk AI agent dimuat otomatis.
- **Markdown rendering** — output model dirender dengan warna (heading, table, code block).
- **KV/D1/PaaS tools** — baca/tulis KV, query D1, create/deploy project langsung dari agent.
- **Tmux supervisor** — spawn dan monitor long-running agent yang survive terminal close.
- **CF Pages/Workers deploy** — helper deploy + build terintegrasi.

## Cara Mulai

### 1. Dapatkan API Key (gratis)

Daftar di **[developers.autokeren.com](https://developers.autokeren.com)** untuk dapatkan API key gratis. Free tier: 20 request/menit.

### 2. Install

```bash
pipx install autokeren
```

> Kalau belum punya pipx: `sudo apt install pipx && pipx ensurepath`
> Alternatif: `pip install --user autokeren`

### 3. Login

```bash
autokeren --login
```

Masukkan API key dari developers.autokeren.com. Selesai.

### 4. Mulai ngoding

```bash
autokeren
```

## Quick Start

### Interactive TUI Chat (Default)

Menjalankan perintah tanpa argumen akan membuka antarmuka TUI interaktif:
```bash
autokeren
```

### Single prompt (Non-interactive)

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

### Deploy aplikasi

```bash
autokeren "deploy toko sepatu sederhana dengan HTML+CSS, pakai D1 untuk produk"
```

Agent akan otomatis create project, tulis kode, dan deploy ke Cloudflare Workers dengan D1 + R2 bindings.

### Contoh percakapan

```
> baca pyproject.toml dan tambahkan field authors
> deploy project ini ke Cloudflare Pages
> jalankan pytest dan perbaiki test yang gagal
> buat web toko sederhana, deploy langsung
> simpan preferensi build ini ke memory
```

## Model Tersedia

| Alias | Model |
|---|---|
| `kimi-code` | Moonshot Kimi K2.7-Code (primary) |
| `kimi-2.6` | Moonshot Kimi K2.6 |
| `glm-5.2` | Zai GLM 5.2 (secondary) |
| `glm-flash` | Zai GLM Flash |
| `llama-4-scout` | Meta Llama 4 Scout |
| `gemma-4` | Google Gemma 4 |
| `nemotron` | NVIDIA Nemotron |

Pilih dengan `-m <alias>`. Default: `kimi-code` dengan fallback ke `glm-5.2`.

## Commands & Shortcuts

Di mode interaktif TUI, Anda dapat menggunakan tombol pintas keyboard (*hotkeys*) dan perintah slash berikut:

### Tombol Pintas Keyboard (Hotkeys)

| Tombol | Aksi | Deskripsi |
|---|---|---|
| **`F1`** | Help | Tampilkan daftar bantuan perintah dan shortcut |
| **`F2`** | Ganti Model | Memunculkan modal dialog interaktif untuk memilih model AI |
| **`F3`** | Reset Sesi | Mereset seluruh percakapan dan status izin tool |
| **`F4`** | Salin Respon | Menyalin pesan/jawaban terakhir AI ke clipboard sistem |
| **`F5`** | Compact | Meringkas riwayat context window percakapan |
| **`Ctrl+Q`**| Keluar | Keluar dari aplikasi autokeren secara aman |

### Perintah Slash

Dapat diketik langsung di kotak input chat:

| Perintah | Deskripsi |
|---|---|
| `/help` | Tampilkan bantuan dan daftar perintah |
| `/q` atau `/quit` | Keluar dari sesi |
| `/model [nama]` | Ganti model aktif (buka modal pop-up jika nama kosong) |
| `/compact` | Ringkas history percakapan, pertahankan N turn terakhir |
| `/reset` | Reset sesi percakapan saat ini |
| `/memory` | Tampilkan lokasi dan isi memory per-project |
| `/permissions` | Tampilkan daftar tool yang diizinkan untuk sesi ini |
| `/save [nama]` | Simpan sesi saat ini |
| `/resume <nama\|id>` | Lanjutkan sesi tersimpan |
| `/sessions` | Daftar semua sesi tersimpan |

## Tools

autokeren membawa 21 tools bawaan dengan permission check dan schema function-calling.

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
| `cf_deploy` | Deploy ke Cloudflare Pages/Workers via wrangler |
| `cf_build_next` | Build Next.js dengan next-on-pages |
| `cf_kv` | Baca/tulis Cloudflare KV namespace |
| `cf_d1` | Jalankan query Cloudflare D1 |
| `create_project` | Buat project PaaS baru (auto D1 + R2 + AI bindings) |
| `deploy_project` | Deploy code ke project PaaS |
| `list_projects` | Daftar project PaaS yang sudah dibuat |
| `tmux` | Supervisor long-running task via tmux |
| `todo` | Kelola todo list multi-step |
| `remember` | Simpan info ke cross-session memory |

## Konfigurasi

Konfigurasi disimpan di `~/.config/autokeren/config.yaml`.

```yaml
cloudflare:
  api_key: ""            # API key dari developers.autokeren.com
  primary_model: "kimi-code"
  secondary_model: "glm-5.2"
  max_tokens: 16384
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
```

### Environment variables

| Variable | Deskripsi |
|---|---|
| `AUTOKEREN_API_KEY` | API key dari developers.autokeren.com (override config) |
| `AUTOKEREN_CONFIG_DIR` | Direktori konfigurasi custom (default `~/.config/autokeren`) |

## Update

```bash
pipx upgrade autokeren
```

## Arsitektur

```
cli.py ──> tui.py (TUI wrapper) ──> agent.py (core loop) ──> models/ (Cloudflare client + router + retry)
                                                              tools/ (Tool base + registry + 21 tools)
                                                              context.py (session memory + token tracking)
                                                              memory.py (cross-session memory)
                                                              session.py (save/resume)
                                                              ui.py (fallback Rich CLI + markdown)
```

## Contributing

Kontribusi sangat diterima. Fork, buat branch, kirim PR.

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Sebelum commit, pastikan `ruff check .`, `mypy autokeren`, dan `pytest` semua lulus.

## License

MIT — lihat [LICENSE](LICENSE).

## Disclaimer

autokeren adalah proyek independen dan **tidak berafiliasi dengan, diendorsing oleh, atau sponsori oleh Cloudflare, Inc.** "Cloudflare" serta produk terkait adalah merek dagang Cloudflare, Inc. autokeren menggunakan infrastruktur dan API publik Cloudflare (Workers AI, D1, R2, KV, Pages) sebagai layanan pihak ketiga.
