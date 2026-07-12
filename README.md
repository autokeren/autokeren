# autokeren

**Cloudflare-first agentic coding CLI with an interactive TUI for developers worldwide.**

**English** | [Bahasa Indonesia](README.id.md) | [简体中文](README.zh-CN.md) | [Português (Brasil)](README.pt-BR.md) | [Español](README.es.md) | [日本語](README.ja.md)

`autokeren` is an agentic coding CLI specifically designed for the Cloudflare-first stack. Built with Python, `autokeren` provides an interactive **Text User Interface (TUI)** that splits the screen into a static status panel and a dynamic chat area. It supports 7 AI models with automatic fallback, and comes equipped with built-in tools for file management, shell execution, git control, Cloudflare deployments, and a built-in PaaS.

[![CI](https://github.com/autokeren/autokeren/actions/workflows/ci.yml/badge.svg)](https://github.com/autokeren/autokeren/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/autokeren.svg)](https://pypi.org/project/autokeren/)

![autokeren TUI Screenshot](docs/assets/autogen-ui-preview.jpg)

---

## Key Features

- **7 AI models** — kimi-code, kimi-2.6, glm-5.2, glm-flash, llama-4-scout, gemma-4, and nemotron with automatic fallback.
- **Built-in PaaS** — deploy applications to Cloudflare Workers directly from the terminal, with automatic D1 + R2 + AI bindings.
- **Multi-Agent Mode & Auto Spawn** — Run multiple agents in parallel via `/project`, or let the primary agent dynamically call sub-agents using the `spawn_agent` tool.
- **MCP Server Support** — Integrate third-party external tools via Model Context Protocol (MCP) and manage them with `/mcp`.
- **Input History** — Navigate previous command entries using the `↑` / `↓` arrow keys in the terminal.
- **Export Chat** — Export the entire chat history as a Markdown file using the `/export` command.
- **Streaming Output** — Token-by-token response rendering in real-time.
- **Permission System** — Prompts for confirmation before executing potentially dangerous shell commands or modifying files.
- **Cross-Session Memory** — Automatically stores and loads project-specific persistent memory upon startup.
- **Session Save/Resume (SQLite)** — Save conversation state to a transactional local SQLite database (`sessions.db`) and resume anytime using slash commands or the `-r` CLI flag.
- **Context Tracking + /compact** — Monitor context window usage and summarize history automatically or manually.
- **AGENTS.md Support** — Automatically loads project-specific instructions for the AI agent.
- **Markdown Rendering** — Rich terminal formatting for headings, tables, and syntax-highlighted code blocks.
- **KV/D1/PaaS Tools** — Read/write KV pairs, run D1 database queries, and manage projects directly from the agent.
- **Tmux Supervisor** — Spawn and monitor long-running background agents that survive terminal closure.
- **CF Pages/Workers Deploy** — Integrated helper tools for building and deploying to Cloudflare.
- **File Explorer (F7)** — Toggle the folder/file tree on the left TUI panel, click a file to automatically read its content.

## Vibe Coding Features (v0.8.0)

9 original features not found in other coding CLIs (Claude Code, Aider, Cursor, Cline):

### Time-Travel `/rewind`
Undo tool calls and restore the codebase to previous checkpoints. Automatically saves a checkpoint after every file write/patch.
```bash
/rewind        # undo 1 tool call
/rewind 3      # undo 3 tool calls
/rewind list   # list all available checkpoints
```

### Architecture Guardian
Index project genome (modules, functions, dependencies) and block duplicate functions/modules before they are written.
```bash
/genome         # view project genome
/genome rescan  # rescan project genome
/genome check   # check for duplicate functions
```

### Loop Breaker
Detect when the agent is stuck in an error/apology/file-thrashing loop. Automatically swaps the active AI model.
```bash
/loop status    # view loop breaker error history
/loop reset     # reset loop tracker
/loop break     # manual break — swap model + reset
```

### Cross-Model Auto-Review
Review unstaged or staged diffs using an AI model from a different vendor to catch blind spots.
```bash
/review         # review unstaged diffs
/review staged  # review staged diffs
```

### Vibe-Security Guard
Automatically scan every file write for secrets, SQL injection, XSS, and forbidden patterns.
```bash
/security           # scan the entire project
/security app.py    # scan a specific file
```

### Live Architecture Enforcement
Rules-based enforcement via `.ak-rules.yaml` (e.g., maximum file lines, forbidden patterns, import limits).

### Spec-Driven Auto-Planning
AI-guided user interview with 20 questions to automatically generate `plan.md` and `technical-plan.md`.
```bash
/spec build a REST API     # start interview
/spec answer my answer     # answer interview questions
/spec generate              # generate implementation plan
/spec show                  # view implementation plan
/spec progress              # track implementation progress
```

### Ghost Agent
Spawn background agents in tmux for parallel task execution.
```bash
/ghost fix bug in login.py  # spawn ghost agent
/ghost list                 # list all background agents
/ghost show 1               # view output of ghost #1
/ghost kill 1               # kill ghost #1
/ghost kill all             # kill all background agents
```

### Research Tool
Deep web search querying Reddit, Hacker News, and Google Web search.
```bash
/research python coding tools     # search all sources
/research reddit asyncio tips     # search Reddit only
/research hn AI coding CLI        # search Hacker News only
/research web best practices      # search Google Web only
```

## AGI Evolution & Self-Healing (v0.11.0+)

Bringing autonomous artificial intelligence to Autokeren CLI:

### 1. Continuous Lifelong Daemon & Observer
An asynchronous background system observer tailing critical error logs and file changes to trigger self-healing processes.

### 2. Self-Evolution / Auto-Refactoring Loop
Automatically refactors broken Python tools, validates them with new pytest unit tests, and hot-reloads the tool registry.

### 3. Local TF-IDF Semantic Memory
High-performance local semantic search using Vector Space Model (VSM) with TF-IDF weighting and Cosine Similarity in a local SQLite database (`memory.db`). No API keys required!

### 4. Interactive Kanban TUI Board (`Ctrl+K`)
Manage project task lists visually inside the terminal, synchronized with local SQLite. Press **`Ctrl+K`** to toggle the board at any time.

### 5. Live Multi-Agent Debate View (`Ctrl+D`)
Monitor discussions, coordination, and work logs of background Ghost Agents in real-time. Press **`Ctrl+D`** to toggle the debate view.

## Installation & Setup

### 1. Get a Free API Key

Sign up at **[developers.autokeren.com](https://developers.autokeren.com)** to get your API key.

### 2. Install

#### Linux / macOS

```bash
pipx install autokeren
```

> If you don't have pipx: `sudo apt install pipx && pipx ensurepath` (Linux) or `brew install pipx` (macOS)
> Alternative: `pip install --user autokeren`

#### Windows (PowerShell)

**Step 1** — Install pipx via pip:

```powershell
python -m pip install --user pipx
```

**Step 2** — Add pipx to Windows PATH:

```powershell
python -m pipx ensurepath
```

**Step 3** — Restart PowerShell (close and reopen the terminal).

**Step 4** — Install autokeren:

```powershell
pipx install autokeren
```

### 3. Login

```bash
autokeren --login
```

Enter your API key from developers.autokeren.com.

### 4. Start Coding

```bash
autokeren
```

## Quick Start

### Interactive TUI Chat (Default)

Launch the interactive TUI interface:
```bash
autokeren
```

### Single Prompt (Non-interactive)

```bash
autokeren "create a hello.py file that prints hello world"
```

### Plan Mode

```bash
autokeren --plan
```

### Resume Saved Session

Resume a saved session directly from the terminal startup:
```bash
autokeren --resume my-session-name
# or using the short flag
autokeren -r my-session-name
```

### Choose Model

```bash
autokeren -m glm "refactor this function"
autokeren -m kimi "write unit tests for the tools module"
```

### Google AI Studio Mode (Gemini API)

Run autokeren directly using your own Google AI Studio API key:
```bash
autokeren --aistudio
```
If your API key is not configured, you will be prompted to enter it. Alternatively, set the `GEMINI_API_KEY` environment variable.

### Deploy Application

```bash
autokeren "deploy a simple shoe shop with HTML+CSS, using D1 for products"
```

The agent will automatically create the project, write the code, and deploy to Cloudflare Workers with D1 and R2 bindings.

## Available Models

| Alias | Model |
|---|---|
| `kimi-code` | Moonshot Kimi K2.7-Code (primary) |
| `kimi-2.6` | Moonshot Kimi K2.6 |
| `glm-5.2` | Zai GLM 5.2 (secondary) |
| `glm-flash` | Zai GLM Flash |
| `llama-4-scout` | Meta Llama 4 Scout |
| `gemma-4` | Google Gemma 4 |
| `nemotron` | NVIDIA Nemotron |

Additional paths:

| Alias | Model |
|---|---|
| `gemini-3.5-flash` | Google Gemini 3.5 Flash via AI Studio (`--aistudio`) |
| `gemini-3.5-pro` | Google Gemini 3.5 Pro via AI Studio (`--aistudio`) |

Select a model with `-m <alias>`. Default: `kimi-code` with fallback to `glm-5.2`.

## Commands & Shortcuts

Use the following keyboard shortcuts and slash commands in TUI mode:

### Keyboard Shortcuts (Hotkeys)

| Key | Action | Description |
|---|---|---|
| **`F1`** | Help | Toggle help dialog listing commands and shortcuts |
| **`F2`** | Switch Model | Open an interactive modal to switch AI models |
| **`F3`** | Reset Session | Reset the conversation history and tool permissions |
| **`F4`** | Copy Response | Copy the last AI message response to the clipboard |
| **`F5`** | Compact | Compact/summarize the conversation history |
| **`F6`** | Switch Language | Open a modal to change the TUI language interface |
| **`F7`** | File Explorer | Toggle the file tree sidebar on the left panel |
| **`Ctrl+K`**| Kanban Board | Toggle the project Kanban board panel |
| **`Ctrl+D`**| Debate View | Toggle the multi-agent background debate view |
| **`Ctrl+C`**| Cancel / Stop | Stop the active AI generation or running shell tool |
| **`Ctrl+Q`**| Force Quit | Force quit the autokeren CLI application |

### Slash Commands

Enter slash commands directly into the chat input box (Tab autocomplete is supported):

| Command | Description |
|---|---|
| `/help` | Display help guidelines |
| `/q` or `/quit` | Exit the CLI session |
| `/model [name]` | Switch AI model (opens pop-up if name is omitted) |
| `/lang [code]` | Switch TUI language (opens pop-up if code is omitted, e.g. `/lang id`) |
| `/export [name]` | Export conversation to a Markdown file |
| `/copy [last\|N]` | Copy a specific message to the clipboard |
| `/mcp` | Open the interactive Model Context Protocol (MCP) server manager |
| `/mcp list` | List active MCP servers |
| `/mcp show <name>` | Show tools from a specific MCP server |
| `/mcp add <name> <cmd>` | Add and start a new MCP server |
| `/config` | View active settings configurations |
| `/config git-commit on\|off` | Toggle automatic git commits |
| `/config cf-verify on\|off` | Toggle auto visual verify after deployment |
| `/local [url]` | Set/view local LLM endpoint (Ollama) |
| `/approval on\|off\|ask` | Set tool execution approval mode |
| `/project <subcommand>`| Multi-agent project management command |
| `/compact` | Compact conversation history |
| `/reset` | Reset the active session |
| `/memory` | View stored cross-session memory for the project |
| `/permissions` | View currently granted tool execution permissions |
| `/save [name]` | Save the current session state |
| `/resume <name\|id>` | Resume a saved session |
| `/sessions` | List all saved sessions |
| `/rewind [N]` | Undo N tool calls and restore codebase to a checkpoint |
| `/rewind list` | List all available checkpoints |
| `/genome` | View codebase structural genome |
| `/genome rescan` | Rescan codebase architecture genome |
| `/genome check` | Scan for duplicate functions |
| `/loop status` | View loop breaker error history |
| `/loop reset` | Reset loop breaker statistics |
| `/loop break` | Break loop manually (swaps active model) |
| `/review [staged]` | Run cross-model code review |
| `/security [file]` | Run security audit scanner on a file |
| `/spec <request>` | Start requirements gathering interview |
| `/spec answer <text>` | Submit answer to interview question |
| `/spec generate` | Generate plan.md and technical-plan.md |
| `/spec show` | View implementation plan |
| `/spec progress` | Track implementation progress |
| `/ghost <task>` | Launch a background ghost agent |
| `/ghost list` | List all running background ghost agents |
| `/ghost show <id>` | View logs of a specific background ghost agent |
| `/ghost kill <id\|all>` | Terminate background ghost agents |
| `/research <query>` | Search Reddit, Hacker News, and Google Web |
| `/deploy <desc>` | Create project and deploy directly to Cloudflare Pages/Workers |

## Stored Configurations

Config file is stored at `~/.config/autokeren/config.yaml`.

```yaml
auth:
  mode: "platform"       # "platform" (default), "direct", or "aistudio"
  api_key: ""            # API key from developers.autokeren.com
  gemini_api_key: ""     # Google AI Studio API key (only for "aistudio" mode)

cloudflare:
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
  max_iterations: 50
  shell_timeout: 180
  shell_allowlist: ["node", "npm", "pnpm", "npx", "git", "wrangler", "python3", "pytest"]
  project_root: "."
  context_window: 262144
  compact_tail_turns: 6
  auto_compact: false
  auto_compact_threshold: 0.8
  # Vibe coding features
  time_travel:
    enabled: true
    max_checkpoints: 50
    auto_checkpoint: true
  architecture_guardian:
    enabled: true
    block_duplicates: true
    scan_interval: 5
  loop_breaker:
    enabled: true
    max_repeats: 3
    auto_switch_model: true
  cross_model_review:
    enabled: true
    reviewer_model: "auto"
    auto_review: false
  vibe_security:
    enabled: true
    scan_on_write: true
    block_on_critical: true
  live_enforcement:
    enabled: true
    rules_file: ".ak-rules.yaml"
    block_on_violation: true
  spec_driven:
    enabled: true
    num_questions: 20
    auto_generate: true
  ghost_agent:
    enabled: true
    max_background: 3
    tmux_prefix: "ak-ghost"
  research:
    enabled: true
    sources: ["reddit", "hackernews", "web"]
    max_results: 10
    max_depth: 3
    summarize: true

mcp_servers:
  - name: filesystem
    enabled: true
    command: ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    env: {}
```

### Environment Variables

| Variable | Description |
|---|---|
| `AUTOKEREN_API_KEY` | Overrides configuration API key |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `AUTOKEREN_CONFIG_DIR` | Custom config directory path (default `~/.config/autokeren`) |

## Update

To upgrade to the latest version:
```bash
pipx upgrade autokeren
```

## Hybrid Go + Python Architecture

`autokeren` utilizes a high-performance hybrid architecture that combines a fast Go interface driver with the flexibility of a Python AI Core:

1.  **Frontend & TUI (Go):**
    Built using **Bubble Tea** and **Lip Gloss**. Manages layout, file explorer tree, input command history, Kanban board, debate panels, and controls the Go-Rod browser automation process.
2.  **Core AI & Brain (Python):**
    Manages the multi-turn agentic loop, multi-model fallback router, static analysis (AST parsing), and security scanning.
3.  **IPC (Inter-Process Communication):**
    Asynchronous **JSON-RPC 2.0** connection established over a **Local TCP Socket** on a dynamic random local port.
    
    *Why Local TCP Socket?*
    This isolates JSON-RPC data packets from the standard output (stdout) stream of the Python process. Any accidental outputs (`print()`) or warnings printed by dependencies are piped directly to background stderr, eliminating parser crashes and TUI freeze bugs.

## Contributing

Contributions are welcome! Please fork the repo, create a feature branch, and submit a PR.

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Before committing code, make sure `ruff check .`, `mypy autokeren`, and `pytest` all pass successfully.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

autokeren is an independent project and is **not affiliated with, endorsed by, or sponsored by Cloudflare, Inc.** "Cloudflare" and its associated product names are trademarks of Cloudflare, Inc. autokeren uses public Cloudflare APIs and workers infrastructure as a third-party client.
