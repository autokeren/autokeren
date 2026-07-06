# Changelog

Semua perubahan penting pada autokeren didokumentasikan di sini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), dan project mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.6.0]: https://github.com/autokeren/autokeren/releases/tag/v0.6.0
[0.5.2]: https://github.com/autokeren/autokeren/releases/tag/v0.5.2
[0.5.1]: https://github.com/autokeren/autokeren/releases/tag/v0.5.1
[0.5.0]: https://github.com/autokeren/autokeren/releases/tag/v0.5.0
[0.4.1]: https://github.com/autokeren/autokeren/releases/tag/v0.4.1
[0.1.0]: https://github.com/autokeren/autokeren/releases/tag/v0.1.0
