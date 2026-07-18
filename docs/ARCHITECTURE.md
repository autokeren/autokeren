# autokeren Architecture

## Overview

autokeren adalah ekosistem developer platform Cloudflare-first untuk Indonesia.

```
User (CLI / Web)
  ↓ ak_ API key
Autokeren API Gateway ─── D1 (auth, usage, legacy projects, Apps V2)
  ↓ privileged platform control plane
Cloudflare (Workers AI, D1, R2, KV, Workers)
```

## Components

### 1. CLI
- Runtime interaktif: Go native; Python 3.11+ dipertahankan sebagai compatibility runtime eksplisit.
- Entry: `autokeren` command.
- Agent loop: model call → tool dispatch → iterate
- Alur beginner publish: `scaffold_app` → source modular + `autokeren.app.json` → `publish_app` → `app_release_status`.
- Dual auth: platform (API key) atau direct (CF credentials)
- UI: TUI Go, streaming, status bar, session, memory, dan permission system.
- Mermaid renderer: visual boxes + arrows di terminal
- Model selector: fetch dari API, nomor + enter

### 2. API Gateway (`autokeren-dev-api`)
- Runtime: Cloudflare Workers
- URL: `api.developers.autokeren.com`
- Endpoints:
  - `GET /v1/models` — list model metadata (public)
  - `POST /v1/chat/completions` — AI inference (auth, streaming, tool calls)
  - `GET /v1/usage` — usage stats (auth)
  - `POST /v1/projects` — legacy one-file Worker project (auth)
  - `POST /v1/projects/:id/deploy` — legacy one-file Worker deploy (auth)
  - `POST /v2/apps/publish` — managed modular app release (auth)
  - `GET /v2/releases/:id` — managed release status (auth)
  - `GET /v2/apps/:id` — managed app/release history (auth)
- Bindings: D1 (DB), KV (RATE_LIMIT), AI (Workers AI)
- Model management: D1 `system_settings` table (free_models, pro_models, model_aliases, models_metadata)

### 3. Web Dashboard (`developers.autokeren.com`)
- Runtime: Cloudflare Pages (Next.js)
- Features: API key management, usage stats, project dashboard (soon), admin panel
- Auth: NextAuth

## Data Flow

### AI Inference (with tool calls)
```
CLI → POST /v1/chat/completions {model, messages, tools, stream}
  ↓
API Gateway:
  1. Validate API key → D1
  2. Check rate limit → KV
  3. Resolve alias → D1 system_settings
  4. Check model access by tier
  5. Forward to env.AI.run(model, {messages, tools, stream})
  6. Return response (streaming SSE atau JSON)
  ↓
CLI parses response:
  - Text: on_chunk callback → terminal
  - Tool calls: parse tc.function.name + arguments
  - Execute tool → append result → loop
```

### Legacy project deploy
```
CLI → POST /v1/projects {name}
  ↓
API Gateway:
  1. Validate API key
  2. Gateway creates D1 database through the platform control plane.
  3. Gateway creates R2 bucket through the platform control plane.
  4. Insert project record → D1
  5. Return {project_id, d1_id, r2_bucket}
  ↓
CLI → POST /v1/projects/:id/deploy {script}
  ↓
API Gateway:
  1. Upload one Worker script through the platform control plane.
  2. Set bindings: D1, R2, AI
  3. Enable workers.dev subdomain
  4. Return {url: "https://{worker}.workers.dev"}
```

### Managed Apps V2

```text
CLI user with only ak_ API key
  ↓ scaffold_app writes an explicit local manifest and declared source files
CLI → POST /v2/apps/publish
  ↓
Gateway validates source, stores immutable R2 artifact, and records queued release
  ↓
Gateway provisions only manifest capabilities, applies checksum-locked migrations,
uploads Worker modules, verifies the public URL, then marks the release ready
  ↓
CLI → GET /v2/releases/:id until ready → verified URL
```

V2 never falls back silently to V1. A failed update keeps the previous verified app URL. Cloudflare account IDs, tokens, Wrangler configuration, and binding IDs remain inside the platform control plane.

## Project Layout

Runtime Go aktif berada di `main.go`, `cmd/`, `internal/`, dan `ui/`. Struktur berikut adalah compatibility runtime Python yang tetap dipertahankan untuk instalasi dan alur legacy eksplisit.

```
autokeren/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── docs/
│   ├── ARCHITECTURE.md     — this file
│   ├── ECOSYSTEM.md        — vision & ecosystem
│   ├── JOURNEY.md          — timeline & milestones
│   ├── ROADMAP.md          — feature priorities
│   ├── DECISIONS.md        — ADR
│   └── RUNBOOK.md          — operations guide
├── autokeren/
│   ├── __init__.py
│   ├── cli.py              — entry, REPL, slash commands
│   ├── config.py           — YAML config, pydantic
│   ├── agent.py            — ReAct loop, tool dispatch
│   ├── context.py          — session memory, token tracking
│   ├── memory.py           — cross-session persistent memory
│   ├── session.py          — save/resume session
│   ├── prompts.py          — system prompt builder
│   ├── ui.py               — rich UI, streaming, permissions
│   ├── utils.py            — helpers (redact, dangerous cmd)
│   ├── selector.py         — model selector
│   ├── mermaid.py          — mermaid block detection
│   ├── diagram.py          — visual box-drawing renderer
│   ├── models/
│   │   ├── base.py         — Message, ModelResponse, ToolCall
│   │   ├── cloudflare.py   — Workers AI client, dual auth
│   │   ├── router.py       — multi-model fallback + circuit breaker
│   │   └── retry.py        — exponential backoff
│   └── tools/
│       ├── base.py         — Tool ABC, ToolResult, ToolRegistry
│       ├── file.py         — read, write, patch, list
│       ├── shell.py        — pty-based shell execution
│       ├── search.py       — ripgrep wrapper
│       ├── web.py          — fetch URL (SSRF-safe)
│       ├── git.py          — git status, diff, commit
│       ├── camofox.py      — e2e browser automation
│       ├── cloudflare.py   — wrangler deploy, build
│       ├── cf_infra.py     — KV, D1 operations
│       ├── tmux.py         — session supervisor
│       ├── todo.py         — task list
│       └── remember.py     — memory storage
└── tests/
    ├── test_tools.py       — 57 tests
    ├── test_mermaid.py     — 10 tests
    └── test_session.py     — 8 tests
```

## Models

| Alias | CF Model ID | Provider | Context |
|---|---|---|---|
| `kimi-code` | `@cf/moonshotai/kimi-k2.7-code` | Moonshot AI | 262K |
| `kimi-2.6` | `@cf/moonshotai/kimi-k2.6` | Moonshot AI | 262K |
| `glm-5.2` | `@cf/zai-org/glm-5.2` | Zhipu AI | 131K |
| `glm-flash` | `@cf/zai-org/glm-4.7-flash` | Zhipu AI | 131K |
| `llama-4-scout` | `@cf/meta/llama-4-scout-17b-16e-instruct` | Meta | 131K |
| `gemma-4` | `@cf/google/gemma-4-26b-a4b-it` | Google | 8K |
| `nemotron` | `@cf/nvidia/nemotron-3-120b-a12b` | NVIDIA | 131K |

Alias mapping di D1 `system_settings.model_aliases`, bisa diubah via admin panel.

## Security

- API key: `ak_live_...` format, stored di D1 dengan hash
- CF API token: stay di API gateway env, ga pernah dikirim ke CLI
- Shell commands: hard block (rm -rf /, mkfs, dd) + soft block (sudo, git push --force) via permission system
- fetch_url: SSRF protection (block private IPs)
- Config file: 0600 permissions, token redacted di logs
