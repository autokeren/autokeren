# Changelog

Semua perubahan penting pada autokeren didokumentasikan di sini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), dan project mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.12.8] - 2026-07-18

### Changed
- fix: align Go runtime recovery with Python

## [0.12.7] - 2026-07-18

### Changed
- fix: start ghost workers on Windows

## [0.12.6] - 2026-07-18

### Changed
- fix: align Go context recovery with Python

## [0.12.5] - 2026-07-18

### Changed
- fix: resolve Windows ghost executable paths

## [0.12.4] - 2026-07-18

### Changed
- fix: preserve Windows environment for ghost agents

## [0.12.3] - 2026-07-18

### Changed
- fix: load ghost configuration across Windows and Unix

## [0.12.2] - 2026-07-18

### Changed
- feat: environment-aware cross-platform tools and resilient Gemini calls

## [0.12.1] - 2026-07-18

### Changed
- fix: native Go provider-aware login and model selection

## [0.12.0] - 2026-07-18

### Changed
- feat: native Go runtime Build Week edition

## [0.11.80] - 2026-07-17

### Changed
- feat: run ghost agents with native Go supervisor

## [0.11.79] - 2026-07-17

### Changed
- fix: render markdown and supervise ghost agents

## [0.11.78] - 2026-07-17

### Changed
- fix: render tool labels without markup leaks

## [0.11.77] - 2026-07-17

### Changed
- fix: render tool output with Rich Markdown formatting

## [0.11.76] - 2026-07-17

### Changed
- fix: prevent markdown markers leaking during TUI streaming

## [0.11.75] - 2026-07-17

### Changed
- docs: update README with actual Codex Session ID

## [0.11.74] - 2026-07-17

### Changed
- fix(polish): clean up trailing whitespaces, refactor path resolver with relative_to, dry schema validation, and expand build week README documentation

## [0.11.73] - 2026-07-17

### Changed
- fix(proof): protect against path traversal, validate replay JSON schema, use atomic UTF-8 writes, and add HTTP integration tests

## [0.11.72] - 2026-07-17

### Changed
- chore: remove Google Antigravity option from login wizard providers list

## [0.11.71] - 2026-07-17

### Changed
- chore: untrack and ignore root ak binary

## [0.11.70] - 2026-07-17

### Changed
- chore: remove kopi-juara project and move handoff doc to private

## [0.11.69] - 2026-07-17

### Changed
- fix(proof): fix argparse CLI flags, make links relative, add replay command, and validate record status

## [0.11.68] - 2026-07-17

### Changed
- feat(proof): implement evidence-led release workflow Autokeren Proof

## [0.11.67] - 2026-07-17

### Changed
- feat(cli): implement interactive multi-provider login and model setup wizard

## [0.11.66] - 2026-07-17

### Changed
- feat(openai): implement native OpenAI model provider supporting Build Week and GPT-5.6

## [0.11.65] - 2026-07-17

### Changed
- docs: update READMEs with new QA features for AST, CAPA, and Tmux sniffing

## [0.11.64] - 2026-07-17

### Changed
- feat(qa): implement AST dependency graphing, CAPA git rollback tags, and background tmux sniffing

## [0.11.63] - 2026-07-16

### Changed
- feat: implement dynamic repo-map, git micro-commits, auto-rollback, and tmux log sniffing

## [0.11.62] - 2026-07-16

### Changed
- fix(agent): make shell tool interruptible and responsive to Ctrl+C

## [0.11.61] - 2026-07-16

### Changed
- fix(ui): fix scroll lock in chat viewport by only auto-scrolling on new messages or user input

## [0.11.60] - 2026-07-15

### Changed
- fix(telegram): fix event loop collision on telegram gateway startup and bypass TUI launch

## [0.11.59] - 2026-07-15

### Changed
- fix(ui): implement dynamic chat text wrapping and dynamic viewport resizing to prevent terminal overflow

## [0.11.58] - 2026-07-15

### Changed
- fix: bypass inner retries and model fallbacks for 8007 context window errors to trigger compaction immediately

## [0.11.57] - 2026-07-15

### Changed
- feat: implement self-healing context window auto-pruning/compaction to prevent error 8007

## [0.11.56] - 2026-07-15

### Changed
- fix(model): limit max_tokens to 4096 to prevent bad request 8007

## [0.11.55] - 2026-07-14

### Changed
- feat: Telegram gateway with typing animation and inline approval

## [0.11.54] - 2026-07-14

### Changed
- feat: proactive auto-compact before model call and configurable FDDM

## [0.11.53] - 2026-07-13

### Changed
- fix: auto-save session on every AI response

## [0.11.52] - 2026-07-13

### Changed
- fix: reset auto-save flag on /reset

## [0.11.51] - 2026-07-13

### Changed
- fix: update existing session on auto-save after resume

## [0.11.50] - 2026-07-13

### Changed
- fix: sidebar session ID display and resume latest partial match

## [0.11.49] - 2026-07-13

### Changed
- fix: auto-save session name sync to Go TUI

## [0.11.48] - 2026-07-13

### Changed
- fix(sidebar): session name langsung update lewat on_model_end notification, bukan polling

## [0.11.47] - 2026-07-13

### Changed
- fix(session): auto-save sesi aktif di semua return path termasuk tool call ## [ interrupt

## [0.11.46] - 2026-07-13

### Changed
- fix(sidebar): tampilkan nama session auto-save langsung di sidebar

## [0.11.45] - 2026-07-13

### Changed
- feat(session): auto-save session setelah respons AI pertama

## [0.11.44] - 2026-07-13

### Changed
- feat(go-tui): add interactive popup input modal for /mcp add in Go TUI

## [0.11.43] - 2026-07-13

### Changed
- fix(go-tui): fix slash commands (/mcp, /config, /local, /approval, /help) in Go TUI

## [0.11.42] - 2026-07-12

### Changed
- feat: add sync slash commands /config, /local, /approval, /mcp to TUI, CLI, Daemon, and Go TUI

## [0.11.41] - 2026-07-12

### Changed
- feat: local LLM support (Pillar A), git auto-commit (Pillar B), visual E2E verification cf_verify (Pillar C)

## [0.11.40] - 2026-07-12

### Changed
- release Simplified Chinese, Spanish, Portuguese, and Japanese README translations

## [0.11.39] - 2026-07-12

### Changed
- add English README translation ## [ link to README.id.md

## [0.11.38] - 2026-07-12

### Changed
- update documentation and changelog for hybrid TCP IPC ## [ SQLite session release

## [0.11.37] - 2026-07-12

### Added
- Integrasi komunikasi IPC menggunakan **Local TCP Sockets** pada port dinamis, menggantikan komunikasi stdio. Ini menyelesaikan masalah *Stdout Pollution* (TUI freeze/crash jika interpreter Python atau dependensi eksternal mencetak data tak terduga ke stdout).
- Migrasi penyimpanan sesi (`save`/`resume`) dari file JSON mentah menjadi database transaksional **SQLite (`sessions.db`)** yang aman dari kerusakan berkas jika proses terputus di tengah jalan.
- Fitur migrasi otomatis untuk memindahkan file sesi JSON lama secara instan ke database SQLite pada awal peluncuran aplikasi.

### Fixed
- Penanganan potensi tabrakan ID sesi pada database SQLite jika pemanggilan penyimpanan dilakukan dengan kecepatan tinggi (milidetik).

## [0.11.36] - 2026-07-12

### Added
- Tampilan status sesi aktif (`session`) secara real-time pada panel sidebar TUI, yang otomatis sinkron dengan perintah `/save`, `/resume`, dan `/reset`.

## [0.11.35] - 2026-07-12

### Added
- Parameter baris perintah `--resume` / `-r` di CLI Python dan Cobra Go untuk memulihkan sesi obrolan lama langsung dari startup terminal (contoh: `autokeren -r revisi-landing`).

## [0.11.34] - 2026-07-12

### Added
- Dukungan perintah slash `/save`, `/resume`, dan `/sessions` langsung ke dalam antarmuka TUI Bubble Tea.

## [0.11.33] - 2026-07-12

### Fixed
- Memperbaiki hang tanpa batas pada elemen kueri browser Go-Rod dengan menerapkan durasi batas waktu (*default timeout*) selama 15 detik.

## [0.11.32] - 2026-07-12

### Fixed
- Memperbaiki thread-safety pemrosesan JSON-RPC pada daemon Python dengan membungkus write stdout ke dalam *thread lock* untuk mencegah terjadinya korupsi byte stream.
- Mengalihkan penanganan perintah pemblokiran panjang (`/compact`, `/reset`, `/save`, dll.) ke background threads agar loop stdin daemon tidak terblokir.

## [0.11.31] - 2026-07-12

### Fixed
- Menghindari aktivasi dini pada input box TUI sebelum seluruh siklus eksekusi agen (multi-turn loop) benar-benar selesai.

## [0.11.30] - 2026-07-12

### Changed
- fix go-rod js eval apply is not a function error and make screenshot save_path fallback robust

## [0.11.29] - 2026-07-12

### Changed
- display real-time human-readable browser actions in the TUI terminal

## [0.11.28] - 2026-07-12

### Changed
- fix camofox tool JSON serialization error by popping python functions from args

## [0.11.27] - 2026-07-12

### Changed
- fix cached Go TUI binary stale issues by checking file modification times during development

## [0.11.26] - 2026-07-12

### Changed
- replace Camofox with native Go-Rod browser automation built directly into the Go TUI binary

## [0.11.25] - 2026-07-12

### Changed
- make camofox tool self-contained by calling the browser server REST API directly

## [0.11.24] - 2026-07-12

### Changed
- add RepoMapTool for codebase structural map indexing and inject curated design presets (Neo-Brutalism, Glassmorphism, Swiss Minimalist) into system prompt

## [0.11.23] - 2026-07-12

### Changed
- fix camofox execution hang by increasing Go IPC buffer limit to 64MB

## [0.11.19] - 2026-07-12

### Changed
- memperbaiki stuck koneksi daemon dan singkronisasi versi TUI lewat env var

## [0.11.18] - 2026-07-12

### Changed
- mengoptimalkan filesystem scanning di observer agar daemon tidak stuck di direktori besar

## [0.11.17] - 2026-07-12

### Changed
- memperbaiki duplikasi session tmux saat memicu ghost agent

## [0.11.16] - 2026-07-12

### Changed
- memperbaiki error TypeError on_output pada pemanggilan tool spawn_agent dan multi-agent

## [0.11.15] - 2026-07-12

### Changed
- update README dengan dokumentasi fitur AGI Evolution (Fase 3 ## [ 4) dan shortcut keyboard TUI baru

## [0.11.14] - 2026-07-12

### Changed
- menambahkan responsive red-white Indonesian flag header dengan versi di sidebar

## [0.11.13] - 2026-07-12

### Changed
- membedakan Ctrl+C untuk interupsi dan Ctrl+Q untuk keluar paksa dari CLI

## [0.11.12] - 2026-07-11

### Changed
- menambahkan shortcut Ctrl+K dan Ctrl+D untuk berpindah tampilan TUI kapan saja

## [0.11.11] - 2026-07-11

### Changed
- implementasi local memory SQLite, TF-IDF search, background system observer daemon, dan self-evolution loop

## [0.11.10] - 2026-07-11

### Changed
- feat: Autonomous Planning Engine (goal decomposition, dynamic replan, reflection) + fix stuck retry when all models down

## [0.11.9] - 2026-07-11

### Changed
- docs: tambahkan panduan build dan deploy komprehensif (BUILD_DEPLOY.md)

## [0.11.8] - 2026-07-11

### Changed
- feat: migrasikan penyimpanan metadata proyek ke SQLite database (.ak-kanban.db)

## [0.11.7] - 2026-07-11

### Changed
- feat: inisialisasi otomatis templat metadata proyek di memory.md

## [0.11.6] - 2026-07-11

### Changed
- feat: tambahkan fitur interupsi Ctrl+C untuk membatalkan loop agen yang stuck tanpa mematikan TUI

## [0.11.5] - 2026-07-11

### Changed
- feat: implementasi otonom Critic-Coder loop (CollaborateTool) untuk multi-agent AGI

## [0.11.4] - 2026-07-11

### Changed
- feat: tambahkan visual panel diskusi/debat multi-agent real-time di TUI

## [0.11.3] - 2026-07-11

### Changed
- feat: perpanjang spawn_agent tool dengan parameter kustom role dan model_id

## [0.11.2] - 2026-07-11

### Changed
- feat: tambahkan aturan otonom Kanban dan Multi-Agent delegation ke system prompt

## [0.11.1] - 2026-07-11

### Changed
- fix: loop self-healing and no-tool stuck protection in agent loop

## [0.11.0] - 2026-07-11

### Changed
- feat: implementasi Ak-Kanban (Kanban Board SQLite-backed) di TUI dan Agent

## [0.10.10] - 2026-07-11

### Changed
- feat: real-time sidebar (auto-refresh) dengan ghost agents dan todo list

## [0.10.9] - 2026-07-11

### Changed
- fix: format log retry rapih, detail sisa ## [ pakai neuron di sidebar

## [0.10.8] - 2026-07-11

### Changed
- fix: context bar akurat, autonomous mode [t], permission dialog clean

## [0.10.7] - 2026-07-11

### Changed
- fix: chat scroll dan neurons quota bar di sidebar

## [0.10.6] - 2026-07-11

### Changed
- fix: .env dan config.yaml sekarang minta izin dulu, tidak langsung diblock

## [0.10.5] - 2026-07-11

### Changed
- feat: bouncing-ball spinner, neuron+context bars, active task in sidebar, remove shortcuts

## [0.10.4] - 2026-07-11

### Changed
- feat: brainwave spinner + 4-option permission dialog with always-allow session memory

## [0.10.3] - 2026-07-11

### Changed
- feat: minimalist professional TUI redesign - clean chat, compact tool activity, typographic sidebar

## [0.10.2] - 2026-07-11

### Changed
- feat: interactive slash command autocomplete dropdown - ketik / untuk lihat menu, navigasi ↑↓, pilih Enter atau 1-5

## [0.10.1] - 2026-07-11

### Changed
- feat: implement interactive model selector popup overlay on /model slash command

## [0.10.0] - 2026-07-11

### Changed
- feat: implement interactive slash command autocomplete and styled file operations feedback

## [0.9.9] - 2026-07-11

### Changed
- fix: auto invalidate cached binary on package version bump to ensure up-to-date execution

## [0.9.8] - 2026-07-11

### Changed
- fix: use subprocess.call instead of execvp on Windows to maintain terminal keyboard raw-mode focus

## [0.9.7] - 2026-07-11

### Changed
- feat: bundle prebuilt Go binaries for Windows, Linux, and macOS inside the wheel package

## [0.9.6] - 2026-07-11

### Changed
- feat: implement hybrid Go TUI and JSON-RPC IPC with cyberpunk theme

## [0.9.5] - 2026-07-11

### Changed
- fix: clean code security, types, and add CLI /debug command

## [0.9.4] - 2026-07-09

### Changed
- fix: fallback parser [TOOL_CALL] text di aistudio

## [0.9.3] - 2026-07-09

### Changed
- **Kembali ke single-line `Input`:** Widget input box dikembalikan dari `TextArea` (multi-line) ke `Input` (single-line). Enter langsung kirim pesan tanpa konflik dengan behavior newline TextArea.
  - `Enter` = kirim pesan (kembali seperti v0.8.8)
  - `↑` / `↓` = navigasi history input
  - Autocomplete slash command (`SuggestFromList`) kembali aktif
- **Restore fitur yang hilang akibat revert tidak sengaja:** Dukungan AI Studio / Antigravity auth mode di `/model` dialog & slash command, `on_retry` callback, `_current_model_name` tracking, dan `getattr` safety guard pada `auth_mode`.

### Fixed
- **Enter tidak respon pada TextArea:** Pada v0.9.2, handler Enter di `on_key` level App tidak reliably menangkap event karena TextArea menelan Enter untuk insert newline. Sekarang pakai `on_input_submitted` (native Input) yang stabil.
- **`_reset_input` & `action_cancel`:** Placeholder input box tidak dikembalikan setelah agent selesai/dibatalkan — sekarang di-reset ke `input_placeholder`.
- **`/model` selalu ke Cloudflare:** Revert sebelumnya menghapus branching `auth.mode == "aistudio"` — sekarang dikembalikan.

## [0.9.2] - 2026-07-09

### Fixed
- **Enter key submit fix on other systems:** Ubah tombol default kirim pesan di `TextArea` menggunakan **Enter** biasa (dan **Shift+Enter** / **Ctrl+Enter** untuk new line). Memperbaiki bugs di komputer lain yang sebelumnya bermasalah/kembali menjadi newline default.
- Memaksa pengosongan teks input area instan sinkron untuk menghindari race conditions.

## [0.9.1] - 2026-07-09

### Fixed
- Bump versi untuk skip v0.8.9/v0.8.10 yang sudah terlanjur publish di PyPI.

## [0.9.0] - 2026-07-09

### Added
- **Multi-line input:** Input box sekarang menggunakan `TextArea` (bukan `Input` single-line). Mendukung multi-line, paste teks panjang, dan unlimited karakter.
  - `Enter` = newline (baru)
  - `Ctrl+Enter` = kirim pesan
  - `Alt+Up` / `Alt+Down` = navigasi history input
- **`/copy [last|N]` command:** Salin pesan ke clipboard. Fallback ke file temp di VPS/SSH.
- **`pyperclip` dependency:** Cross-platform clipboard support.

### Fixed
- **F4 (Salin Respon) broken:** Method `copy_to_clipboard` tidak ada implementasinya. Sekarang pakai `_copy_text()` dengan fallback chain: pyperclip → xclip → xsel → wl-copy → pbcopy → save to temp file.
- **Gemini 3.5 `thought_signature` error:** Flatten tool call history ke plain text untuk model thinking (Gemini 3.5/3.0). Native function calling tetap dipakai pada turn saat model merespons.
- **Windows PermissionError di genome scanner:** `iterdir()` pada junction/symlink Windows (misal `Application Data`) menyebabkan `PermissionError`. Sekarang semua pemanggilan `iterdir()` di scanner dibungkus try/except `(PermissionError, OSError)`.

### Changed
- Default model AI Studio: `gemini-1.5-flash` → `gemini-3.5-flash`.
- History navigation: `Up/Down` → `Alt+Up/Alt+Down` (karena Up/Down sekarang untuk cursor di TextArea).
- Input suggester (autocomplete slash command) dihapus karena TextArea tidak mendukung `SuggestFromList`.

## [0.8.8] - 2026-07-08

### Fixed
- **Gemini 3.5 `thought_signature` error:** Saat tool result dikirim ulang ke history, Gemini 3.5 menolak native `functionCall` karena missing `thought_signature`. Solusi: flatten riwayat tool calls menjadi plain text (`[TOOL_CALL name=...]` / `[TOOL_RESULT name=...]`) sebelum dikirim ke API. Native function calling tetap dipakai pada turn saat model merespons. Model Gemini 1.5 tidak terkena masalah ini dan tetap native.
- **Default model AI Studio:** `gemini-1.5-flash` → `gemini-3.5-flash` agar sejalan dengan model terbaru yang didukung AI Studio integration.

### Changed
- Update `tests/test_aistudio.py` ekspektasi model ID ke `gemini-3.5-flash`/`gemini-3.5-pro`.

## [0.8.7] - 2026-07-08

### Added
- **Google AI Studio Integration (`--aistudio`):** Dukungan native untuk model-model Google AI Studio (Gemini API) menggunakan API Key pribadi. Dilengkapi dengan auto-fetch model list langsung dari endpoint Google, streaming SSE, parameter generationConfig, dan penanganan format tools/function calling secara otomatis.
- **Auto-setup API Key:** Pengecekan otomatis untuk API Key Google AI Studio lewat env var `GEMINI_API_KEY` dan prompt interaktif penyimpanan key ke `config.yaml`.

## [0.8.6] - 2026-07-08

### Fixed
- **CF error 3040 (max output exceeded):** `max_tokens` 16384→8192. CF Workers AI models max ~8K output tokens. BE clamp juga 8192. Strategi tulis Worker bertahap (write + patch) makin penting.

## [0.8.5] - 2026-07-08

### Fixed
- **Worker full-stack terpotong:** System prompt sekarang instruksikan AI tulis Worker bertahap — `write_file` base structure (max 300 baris), lalu `patch_file` untuk tambah CSS/JS/API routes via placeholder (`/* STYLES */`, `/* SCRIPT */`). Bukan lagi "inline everything in one file" yang bikin terpotong oleh limit token.
- **Rate limit handling:** CLI sekarang baca `Retry-After` header dari BE pas kena 429, dan tunggu sesuai sebelum retry. Retry policy honor `retry_after` dari server.
- **Model name tidak update:** Pas `/model` switch di TUI, `_current_model_name` tidak di-update. Fixed di CLI, TUI `/model`, dan TUI model select screen.

### Changed
- `/deploy` command prompt updated: instruksikan AI tulis Worker bertahap (write + patch), bukan sekaligus.
- Rate limit free tier 20→60 req/min, pro tier 100→200 req/min.
- Rate limit bisa di-set via env var `RATE_LIMIT_FREE` / `RATE_LIMIT_PRO` di BE.
- BE `max_tokens` hard cap 16384 (clamped di dispatch.ts).
- BE AI deploy scanner tambah fallback models (Llama 4 Scout, GLM Flash).
- TUI user message punya background `#1a1a2e` biar beda dari chat area.
- TUI ToolWidget tampilkan tool name di success/error state (`✓ read_file summary`).
- Thinking spinner tampilkan timer + model name (`mikir (5s) kimi-code`).

## [0.8.4] - 2026-07-08

### Added
- **`/deploy` command:** Shortcut untuk bikin app + deploy ke Cloudflare dalam satu command. `/deploy <deskripsi>` → AI auto create_project → write_file → deploy_project → URL live.
- **Thinking timer + model info:** Spinner "mikir" sekarang tampilkan elapsed time `(5s)` dan nama model aktif. Kuning kalau >10 detik.
- **Tool execution detail:** Tool status sekarang tampilkan verb (`nulis file…`, `baca file…`, `jalankan command…`) + elapsed time di result.
- **Retry visibility:** Auto-retry sekarang tampil ke user: `↻ retry #2 (2s) — timeout`. Termasuk model fallback: `↻ fallback ke model: glm-5.2`.
- **Rate limit env override:** Backend rate limit bisa di-set via env var `RATE_LIMIT_FREE` / `RATE_LIMIT_PRO`.
- **System prompt best practices:** AI sekarang diinstruksikan untuk max 500 baris per file, pecah ke modular files.

### Fixed
- **File terpotong:** `read_file` limit 200→500 baris, `to_string` & context 8000→20000 chars. Root cause utama: config user `max_tokens: 4096` (kekecilan, model kehabisan token mid-generation).
- **Streaming timeout 10 menit:** Read timeout 120s→60s. Sebelumnya 5 retry × 120s = 10 menit stuck.
- **Guardian terlalu ketat:** `block_duplicates` default `True`→`False` (warn only, tidak block write). Guardian sekarang kirim warning ke context, bukan block.
- **Model name tidak update:** Pas `/model` switch, nama model di thinking spinner tidak ter-update. Fixed di CLI dan TUI.
- **Tool name hilang di TUI:** ToolWidget hanya tampilkan `✓ summary` tanpa tool name. Sekarang `✓ read_file summary`.
- **BE max_tokens clamp:** Backend clamp `max_tokens` ke 16384 (sebelumnya 200000 yang bikin CF Workers AI timeout).
- **BE rate limit message:** "req/day" → "req/min" (sesuai aktual).
- **BE AI scanner fallback:** Tambah fallback model (Llama 4 Scout, GLM Flash) kalau Gemma 4 down.
- **User message canvas:** TUI user message sekarang punya background `#1a1a2e` biar beda dari chat area.

### Changed
- Rate limit free tier 20→60 req/min, pro tier 100→200 req/min.
- `max_tokens` default 16384 (realistik untuk CF Workers AI models).

## [0.8.2] - 2026-07-07

### Added
- **File Explorer (F7):** Toggle folder/file tree di panel kiri TUI. Tekan F7 untuk show/hide, click file → auto `read_file` → isi file tampil di chat. Pakai `DirectoryTree` Textual (lazy-load, tidak scan semua di startup).
- **AI Deploy Scanner:** Backend API gateway sekarang scan semua deploy pakai AI (Gemma 4 26B) + regex quick-scan. Block phishing, malware (eval/atob), XSS, brand impersonation. Configurable via `SCAN_MODEL` env var.

### Fixed
- **Windows startup hang:** GenomeScanner ganti `rglob("*")` ke manual walk yang skip ignored dirs. Genome scan jadi lazy (cuma scan saat first write_file/patch_file, bukan di startup).
- **TUI key conflict:** Up/Down keys cuma trigger input history saat input pane focused, tidak mencuri navigasi dari File Explorer.

## [0.8.0] - 2026-07-07

### Added — 9 Vibe Coding Features

Satu-satunya CLI yang punya 9 fitur ini. Tidak ada di Claude Code, Aider, Cursor, opencode, atau Cline.

#### Phase 1 — Core Differentiators
- **Time-Travel `/rewind`:** Undo tool calls dan restore codebase ke checkpoint sebelumnya. Auto-checkpoint setelah setiap write_file/patch_file. Slash: `/rewind N`, `/rewind list`.
- **Architecture Guardian:** Scan project genome (modules, functions, dependencies), block pembuatan duplikat function/module sebelum write. Slash: `/genome`, `/genome rescan`, `/genome check`.
- **Loop Breaker:** Deteksi agent stuck di loop (same error N kali, same tool+args, apology loop). Auto-swap model, inject system message. Slash: `/loop status`, `/loop reset`, `/loop break`.

#### Phase 2 — Quality & Safety
- **Cross-Model Auto-Review:** Review code diff dengan model dari vendor berbeda (kimi↔glm) untuk catch blind spots. Slash: `/review`, `/review staged`.
- **Vibe-Security Guard:** Scan otomatis setiap file write untuk secrets, SQLi, XSS, forbidden code (eval). Block pada CRITICAL findings. Slash: `/security`, `/security <file>`.
- **Live Architecture Enforcement:** Rules-based enforcement via `.ak-rules.yaml` — max file lines, forbidden patterns, import restrictions. Block sebelum write.

#### Phase 3 — Productivity
- **Spec-Driven Auto-Planning:** AI interview user dengan 20 pertanyaan clarifying, generate `plan.md` + `technical-plan.md`, track progress per step. Slash: `/spec <request>`, `/spec answer <text>`, `/spec generate`, `/spec show`, `/spec progress`.
- **Ghost Agent:** Spawn background agent di tmux session terpisah untuk parallel work. `--non-interactive --task "..."` CLI mode untuk ghost agent. Slash: `/ghost <task>`, `/ghost list`, `/ghost show <id>`, `/ghost kill <id>|all`.

#### Phase 4 — Research
- **Research Tool:** Deep research ke Reddit (.json API), Hacker News (Algolia API), dan Web (DuckDuckGo). Fetch threads + comments, LLM summarize jadi laporan riset. Slash: `/research <query>`, `/research reddit|hn|web <query>`.

### Changed
- **Version bump:** 0.7.6 → 0.8.0
- **Config:** 6 config section baru: `time_travel`, `architecture_guardian`, `loop_breaker`, `cross_model_review`, `vibe_security`, `live_enforcement`, `spec_driven`, `ghost_agent`, `research`.
- **Agent loop:** Hooks untuk auto-checkpoint, guardian check, enforcer check, loop detection, security scan, pattern detection terintegrasi di `agent.py`.
- **TUI:** Semua 9 slash command baru tersedia di TUI mode (`tui.py`).
- **CLI:** Argumen baru `--non-interactive` dan `--task` untuk ghost agent mode.
- **Tools:** Tool baru terdaftar: `rewind`, `genome`, `review`, `research`.

### Stats
- **163 tests** (was 130, +33 new tests across 3 features)
- **75 source files** type-checked dengan mypy strict
- **0 ruff errors, 0 mypy errors**

## [0.7.6] - 2026-07-07

### Fixed
- **Slash Command Input Stuck:** `_agent_running` guard flag di-set sebelum cek slash command, menyebabkan input ke-block selamanya setelah `/help`, `/model`, dll. Fix: pindahkan setelah slash command check.

## [0.7.5] - 2026-07-07

### Added
- **Windows PowerShell Install Instructions:** README sekarang punya langkah-langkah install pipx di Windows (pip install → ensurepath → restart → pipx install).

## [0.7.4] - 2026-07-07

### Added
- **Dynamic AI Language Response:** AI diinstruksikan merespon dalam bahasa yang dipilih user di UI.

## [0.7.3] - 2026-07-07

### Fixed
- **Mermaid Flicker:** Disable mermaid image rendering by default (config: `mermaid_render: false`). Mermaid blocks sekarang dirender sebagai code block. Ketik `/diagram` untuk render manual.
- **429 Fallback Bug:** Router ga fallback ke secondary model saat primary kena 429 (rate limit). Sekarang semua error langsung fallback.

## [0.7.2] - 2026-07-07

### Added
- **Clipboard Paste Detection:** Input panjang (>80 chars) atau multi-line paste ditampilkan sebagai blok kuning dengan char count. User bisa ketik lagi sebelum kirim.

## [0.7.1] - 2026-07-07

### Fixed
- **Double Render (Streaming):** `Live(transient=True)` menyebabkan content hilang saat streaming selesai, lalu di-render ulang = doble. Fix: `transient=False` + `_final_render()` sebelum stop.
- **Resume Orphaned Tool Calls:** Session yang di-save di tengah eksekusi punya orphaned tool_calls → API bingung → model looping. Fix: hapus orphaned tool_calls saat resume.
- **Markdown Streaming Throttle:** Throttle render ke max 1 per 80ms (12fps) untuk kurangi flicker.

## [0.7.0] - 2026-07-07

### Fixed
- **Windows Support:** `pty` dan `termios` adalah Unix-only. Conditional import + `_run_subprocess()` fallback untuk Windows (subprocess.Popen dengan PIPE).
- **Windows Input Loop:** `Input.Submitted` bisa fire berkali-kali di Windows sebelum `disabled=True` efektif. Fix: `_agent_running` boolean guard flag.
- **Max Iterations:** 25→50, system prompt instruct model to converge (jangan loop tool calls tanpa henti).
- **Max Tool Calls:** Unlimited (0) — batas alami: context window + neuron quota.
- **Pager Stuck:** `GIT_PAGER=cat` dan `PAGER=cat` di shell environment — prevent stuck pada `git log`, `git diff`.
- **Animated "mikir" Spinner:** Custom spinner `mikir .` → `mikir ..` → `mikir ...` (350ms interval).
- **Markdown Streaming:** Streaming sekarang render Markdown (code highlight, heading, bold, list) real-time, bukan plain text.

## [0.6.8] - 2026-07-06

### Added
- **Verbose TDD Execution Logging:** TDD engine sekarang mencetak visualisasi kode unit test, kode implementasi, kode hasil refactor, serta potongan error dari test runner (`pytest`) ke panel obrolan TUI secara real-time. Proses TDD tidak lagi berupa "black box".

## [0.6.7] - 2026-07-06

### Fixed
- **TDD Thread RuntimeError:** Memperbaiki crash RuntimeError `call_from_thread` di Textual saat perintah `/tdd` dijalankan dengan memanggil UI state changer secara langsung di thread utama.

## [0.6.6] - 2026-07-06

### Added
- **Multi-Agent TDD Engine (/tdd):** Implementasi alur kerja Red-Green-Refactor otomatis. CLI/TUI sekarang mendukung perintah `/tdd <nama_file> | <spesifikasi_fitur>` untuk meluncurkan kolaborasi RED (Tester) dan BLUE (Coder) Agent secara live di background thread menggunakan test runner lokal.

## [0.6.5] - 2026-07-06

### Fixed
- **PyPI Update CLI Notification:** Mengubah instruksi pembaruan (upgrade) aplikasi di notifikasi TUI agar menggunakan `pipx upgrade autokeren` (sesuai rekomendasi utama di README) alih-alih `pip install`.

## [0.6.4] - 2026-07-06

### Added
- **Inline Write-File Preview Visualization:** Menampilkan visualisasi potongan kode baru/timpa secara langsung (inline) di terminal CLI (`ui.py`) dan TUI (`tui.py`) lengkap dengan nomor baris (maksimal 20 baris pertama) saat file sukses ditulis menggunakan `write_file`.

## [0.6.3] - 2026-07-06

### Added
- **Inline Code Snippet Diff Visualization:** Menampilkan visualisasi potongan kode diff secara langsung (inline) di terminal CLI (`ui.py`) dan TUI (`tui.py`) lengkap dengan nomor baris saat file sukses diedit menggunakan `patch_file`.

## [0.6.2] - 2026-07-06

### Fixed
- **Instant Ctrl+C Cancellation Recovery:** Tombol `Ctrl+C` sekarang langsung mengaktifkan kembali dan memfokuskan input box percakapan secara instan, tanpa harus menunggu background thread/subprocess (seperti shell execution atau API request) selesai dibatalkan.

## [0.6.1] - 2026-07-06

### Added
- **Default Auto-Focus on Startup:** Kursor input chat langsung aktif saat aplikasi TUI/terminal pertama kali dibuka.
- **Auto-Focus fixes:** Kursor otomatis fokus kembali setelah modal dismiss (model, language, mcp) atau slash command selesai.

### Fixed
- **Interactive MCP Manager:** Memungkinkan penambahan server baru langsung via form input di modal, dan tersimpan ke config.yaml.

## [0.6.0] - 2026-07-06

### Added
- **Multi-Agent Mode:** Perintah `/project` (`new`, `add`, `run`, `status`, `output`, `list`, `switch`) untuk menjalankan beberapa agent secara paralel.
- **SpawnAgentTool:** Memungkinkan agent utama secara otomatis menjalankan sub-agent untuk membagi task secara mandiri.
- **MCP Server Support:** Dukungan Model Context Protocol (MCP) dengan client JSON-RPC stdio.
- **Interactive MCP Manager:** Akses via `/mcp` untuk melihat status server aktif, mendaftar tools, dan menambahkan server baru secara langsung.
- **Input History:** Navigasi input dengan tombol arah `↑` / `↓` di TUI.
- **Export Chat:** Perintah `/export` untuk mengekspor percakapan ke Markdown file.
- **Git-Aware Tools:** Penambahan tool `git_log` dan `git_branch`.
- **Auto-Focus Input:** Kursor input secara otomatis kembali fokus setelah modal ditutup atau command selesai.

## [0.5.2] - 2026-07-05

### Added
- **Multi-Language Support (i18n):** Antarmuka TUI mendukung 8 bahasa (ID, EN, ZH, JA, DE, AR, ES, PT) dengan tombol `F6` untuk mengganti bahasa secara instan.
- **Ctrl+C Generation Cancel:** Batalkan proses AI aktif secara dinamis.
- **Dynamic Localization:** AI diinstruksikan merespon dalam bahasa yang aktif di UI.

### Fixed
- **TUI Scrolling:** Auto-scrolling responsif tanpa jeda (lag) dan anti-overflow.

## [0.5.1] - 2026-07-04

### Added
- Asynchronous update checker untuk mengecek rilis terbaru di PyPI saat program dinyalakan.

## [0.5.0] - 2026-07-04

### Added
- **Full Textual TUI:** Tampilan CLI interaktif minimalis bergaya Antigravity.
- Panel status informasi di bagian kiri TUI.
- Interactive modal selector untuk mengganti model AI secara langsung.
- Penyetujuan rencana kerja via pop-up modal.
- `F4` hotkey untuk menyalin respon terakhir ke clipboard sistem.

### Fixed
- Kebocoran markup error pada teks mentah di Rich.

## [0.4.1] - 2026-07-04

### Added
- Deteksi penempelan clipboard (paste detection) untuk input panjang di TUI.

## [0.1.0] - 2026-07-04

### Added
- Initial release.
- Core agentic loop (`agent.py`) dengan multi-iteration tool dispatch.
- Cloudflare Workers AI client dengan HTTP/2 streaming output.
- Multi-model fallback otomatis: Kimi K2.7-Code (primary) dan GLM 5.2 (secondary).
- Retry dengan exponential backoff, jitter, dan circuit breaker.
- Permission system dengan shell allowlist dan dangerous-command blocklist.
- Cross-session memory per-project (`MemoryManager` + `remember` tool).
- Session save/resume (`session.py`, perintah `/save` dan `/resume`).
- Context tracking dengan token usage dan perintah `/compact` (manual + auto-compact).
- AGENTS.md support: instruksi per-project dimuat otomatis ke system prompt.
- Indonesian localization untuk seluruh UI text.
- 18 tools bawaan.

[0.8.2]: https://github.com/autokeren/autokeren/releases/tag/v0.8.2
[0.8.1]: https://github.com/autokeren/autokeren/releases/tag/v0.8.1
[0.8.0]: https://github.com/autokeren/autokeren/releases/tag/v0.8.0
[0.7.6]: https://github.com/autokeren/autokeren/releases/tag/v0.7.6
[0.7.5]: https://github.com/autokeren/autokeren/releases/tag/v0.7.5
[0.7.4]: https://github.com/autokeren/autokeren/releases/tag/v0.7.4
[0.7.3]: https://github.com/autokeren/autokeren/releases/tag/v0.7.3
[0.7.2]: https://github.com/autokeren/autokeren/releases/tag/v0.7.2
[0.7.1]: https://github.com/autokeren/autokeren/releases/tag/v0.7.1
[0.7.0]: https://github.com/autokeren/autokeren/releases/tag/v0.7.0
[0.6.8]: https://github.com/autokeren/autokeren/releases/tag/v0.6.8
[0.6.7]: https://github.com/autokeren/autokeren/releases/tag/v0.6.7
[0.6.6]: https://github.com/autokeren/autokeren/releases/tag/v0.6.6
[0.6.5]: https://github.com/autokeren/autokeren/releases/tag/v0.6.5
[0.6.4]: https://github.com/autokeren/autokeren/releases/tag/v0.6.4
[0.6.3]: https://github.com/autokeren/autokeren/releases/tag/v0.6.3
[0.6.2]: https://github.com/autokeren/autokeren/releases/tag/v0.6.2
[0.6.1]: https://github.com/autokeren/autokeren/releases/tag/v0.6.1
[0.6.0]: https://github.com/autokeren/autokeren/releases/tag/v0.6.0
[0.5.2]: https://github.com/autokeren/autokeren/releases/tag/v0.5.2
[0.5.1]: https://github.com/autokeren/autokeren/releases/tag/v0.5.1
[0.5.0]: https://github.com/autokeren/autokeren/releases/tag/v0.5.0
[0.4.1]: https://github.com/autokeren/autokeren/releases/tag/v0.4.1
[0.1.0]: https://github.com/autokeren/autokeren/releases/tag/v0.1.0
