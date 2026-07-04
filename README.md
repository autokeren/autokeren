# autokeren

Agentic coding CLI buat developer Indonesia dan global, dibangun Cloudflare-first.

Bedanya dengan opencode / Claude Code:
- **Multi-model fallback otomatis**: Kimi K2.7-Code ↔ GLM 5.2, dengan retry + circuit breaker.
- **Camofox built-in**: automation browser end-to-end tanpa setup tambahan.
- **Cloudflare native helpers**: deploy Pages/Workers, tail logs, KV/D1-aware out of the box.
- **Tmux supervisor**: spawn dan monitor long-running agent yang survive terminal close.
- **Pluggable tools**: taruh tool custom di `~/.config/autokeren/tools/`.
- **Open source + gratis tier via Autokeren Gateway** (regenerasi token di `developers.autokeren.com`).

## Features
- Native Cloudflare Workers AI: **GLM 5.2** and **Kimi K2.7-Code**.
- Auto-retry with exponential backoff, model fallback, and circuit breaker.
- Built-in tools: file, shell, search, web, git.
- Camofox end-to-end automation (profile-based).
- Cloudflare Pages / Workers deployment helpers.
- Tmux supervisor for long-running tasks.
- Transparent YAML config.

## Install

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure

```bash
autokeren --init
```

Atau copy `config.example.yaml` ke `~/.config/autokeren/config.yaml` dan isi `account_id` serta `api_token` Cloudflare Workers AI.

## Usage

```bash
# Interactive chat
autokeren

# Single prompt
autokeren "buat file hello.py yang cetak hello world"

# Plan mode
autokeren --plan

# Pakai model GLM
autokeren -m glm "refactor fungsi ini"
```

## License

MIT — lihat [LICENSE](LICENSE).
