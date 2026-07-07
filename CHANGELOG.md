# Changelog

Semua perubahan penting pada autokeren didokumentasikan di sini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), dan project mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
