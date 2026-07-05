# autokeren Architecture

## Overview

autokeren adalah ekosistem developer platform Cloudflare-first untuk Indonesia.

```
User (CLI / Web)
  ↓ API key
API Gateway (Workers) ─── D1 (auth, usage, projects)
  ↓ CF API Token          KV (rate limit)
Cloudflare (Workers AI, D1, R2, Pages, Workers)
```

## Components

### 1. CLI (`autokeren/`)
- Bahasa: Python 3.11+
- Entry: `autokeren` command
- Agent loop: model call → tool dispatch → iterate
- 20 tools: file, shell, search, git, camofox, cf_deploy, cf_kv, cf_d1, tmux, todo, remember, create_project (soon), deploy_project (soon)
- Dual auth: platform (API key) atau direct (CF credentials)
- UI: rich-based, inline streaming, status bar, permission system
- Mermaid renderer: visual boxes + arrows di terminal
- Model selector: fetch dari API, nomor + enter

### 2. API Gateway (`autokeren-dev-api`)
- Runtime: Cloudflare Workers
- URL: `api.developers.autokeren.com`
- Endpoints:
  - `GET /v1/models` — list model metadata (public)
  - `POST /v1/chat/completions` — AI inference (auth, streaming, tool calls)
  - `GET /v1/usage` — usage stats (auth)
  - `POST /v1/projects` — create project (soon, auth)
  - `POST /v1/projects/:id/deploy` — deploy worker (soon, auth)
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

### Project Deploy (planned)
```
CLI → POST /v1/projects {name}
  ↓
API Gateway:
  1. Validate API key
  2. Create D1 database (wrangler d1 create)
  3. Create R2 bucket (wrangler r2 bucket create)
  4. Insert project record → D1
  5. Return {project_id, d1_id, r2_bucket}
  ↓
CLI → POST /v1/projects/:id/deploy {script}
  ↓
API Gateway:
  1. Upload Worker script (CF API)
  2. Set bindings: D1, R2, AI
  3. Enable workers.dev subdomain
  4. Return {url: "https://{worker}.workers.dev"}
```

## Project Layout (CLI)
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
