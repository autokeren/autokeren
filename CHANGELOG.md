# Changelog

Semua perubahan penting pada autokeren didokumentasikan di sini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), dan project mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- 18 tools bawaan:
  - File: `read_file`, `write_file`, `patch_file`, `list_files`
  - Shell: `run_shell`
  - Search: `search_code`
  - Web: `fetch_url`
  - Git: `git_status`, `git_diff`, `git_commit`
  - Cloudflare: `cf_deploy`, `cf_build_next`, `cf_kv`, `cf_d1`
  - Camofox: `camofox` (browser e2e automation)
  - Tmux: `tmux` (long-running supervisor)
  - Productivity: `todo`, `remember`
- Slash commands: `/help`, `/q`, `/status`, `/compact`, `/reset`, `/memory`, `/save`, `/resume`, `/sessions`.
- Rich-based terminal UI dengan banner, panel, dan streaming.
- Transparent YAML config (`config.example.yaml`).
- PyPI packaging via hatchling.

[0.1.0]: https://github.com/autokeren/autokeren/releases/tag/v0.1.0
