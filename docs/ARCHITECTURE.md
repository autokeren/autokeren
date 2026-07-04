# autokeren Architecture

A custom agentic coding CLI built for the Cloudflare-first stack used by Dialro, AutoKeren, and CeritaSuaraIbu.

## Goals
- Be better than generic agents (opencode / Claude Code / aider) for our specific stack.
- Native Cloudflare Workers AI models: GLM 5.2 and Kimi K2.7-Code.
- Resilient inference: auto-retry, model fallback, circuit breaker, cost tracking.
- Native e2e automation through Camofox (localhost:9377).
- Native deployment through Wrangler / next-on-pages.
- Native long-running supervision through tmux.
- Transparent config: every line is human-readable YAML.

## Stack
- Python 3.11+
- `httpx` for HTTP/2 streaming
- `rich` for terminal UI
- `pydantic` for config + tool schemas
- `pyyaml` for config
- `strictyaml` optional later for validation
- standard library only for core tools

## Project Layout
```
autokeren/
├── pyproject.toml
├── README.md
├── docs/
│   └── ARCHITECTURE.md
├── autokeren/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py            # entry point, argument parsing, chat loop
│   ├── config.py         # YAML config load/save/defaults
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py       # Message, TokenUsage, ModelResponse
│   │   ├── router.py     # multi-model fallback + cost tracking
│   │   ├── retry.py      # RetryPolicy, circuit breaker, jitter
│   │   └── cloudflare.py # Cloudflare Workers AI client
│   ├── agent.py          # ReAct loop, streaming, plan/execute mode
│   ├── context.py        # project indexing, memory, cost/session state
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py       # Tool, ToolResult, registry
│   │   ├── file.py       # read, write, patch, list
│   │   ├── shell.py      # execute shell commands
│   │   ├── search.py     # grep/ripgrep wrapper
│   │   ├── web.py        # fetch web pages
│   │   ├── git.py        # git status, diff, commit helpers
│   │   ├── camofox.py    # Camofox REST bridge e2e tool
│   │   ├── cloudflare.py # wrangler/next-on-pages deploy helpers
│   │   └── tmux.py       # tmux session/pane supervisor
│   ├── prompts.py        # system prompt(s)
│   └── utils.py          # small helpers
└── tests/
    └── test_placeholder.py
```

## Model Abstraction
### Message format
OpenAI-compatible:
```python
{"role": "system" | "user" | "assistant" | "tool", "content": str, "name?": str, "tool_call_id?": str}
```

### Cloudflare Workers AI client
- Endpoint: `POST /client/v4/accounts/{account_id}/ai/run/{model_id}`
- Streaming supported through `text/event-stream` for some models; fallback to JSON.
- Supports `tools` array and `tool_choice: "auto"`.
- Model IDs default to:
  - `@cf/moonshotai/kimi-k2.7-code`
  - `@cf/zai-org/glm-5.2`

### Retry policy
```python
class RetryPolicy:
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: set = {408, 429, 500, 502, 503, 504}
```

### Model router
- Primary model attempts first.
- On 429/5xx/timeout, back off and retry within same model.
- After local max retries, failover to secondary model.
- Circuit breaker per model: if 5 failures in 60s, open for 30s.
- Tracks per-call cost/usage and per-session totals.

## Tool System
Each tool is a Python class with:
- `name`: str
- `description`: str
- `parameters`: JSON Schema dict
- `run(**kwargs) -> ToolResult`

Tools are registered in `ToolRegistry` and passed to the model as OpenAI function schemas.

### Built-in tools
1. **File**
   - `read_file(path, offset, limit)`
   - `write_file(path, content)` (with backup)
   - `patch_file(path, old_string, new_string)`
   - `list_files(path, recursive)`
2. **Shell**
   - `run_shell(command, timeout, workdir)` with allow/blocklist guards
3. **Search**
   - `search_code(pattern, path, file_glob)` ( ripgrep )
4. **Web**
   - `fetch_url(url)` markdown via local extraction or simple fetch
5. **Git**
   - `git_status(path)`
   - `git_diff(path)`
   - `git_commit(message, path)`
6. **Camofox (e2e)**
   - `camofox_navigate(url, profile)`
   - `camofox_snapshot(profile)`
   - `camofox_click(ref, selector, profile)`
   - `camofox_type(text, ref, selector, press_enter, profile)`
   - `camofox_eval(expression, profile)`
   - `camofox_screenshot(profile, save_path)`
   - `camofox_assert_visible(text_or_selector, profile)`
7. **Cloudflare deploy**
   - `cf_deploy_pages(path, project_name)` (wrangler pages deploy)
   - `cf_deploy_worker(path, name)` (wrangler deploy)
   - `cf_tailworker(name)` (wrangler tail)
   - `cf_build_next_on_pages(path)`
8. **Tmux supervisor**
   - `tmux_run(command, session, window, background, notify)`
   - `tmux_capture(session, window, pane, lines)`
   - `tmux_kill(session)`
   - `tmux_list()`

## Agent Loop
- ReAct with tool calls.
- Streaming raw text deltas; tool calls delivered as artifacts.
- Max iterations default 25.
- Plan mode: first respond with a numbered plan, wait for user approval, then execute.
- After each tool call, a tool result message is appended to context.
- Context manager trims old messages when near model context limit and keeps a running summary.

## Configuration
`~/.config/autokeren/config.yaml`:
```yaml
cloudflare:
  account_id: ""
  api_token: ""   # Cloudflare Workers AI token
  models:
    primary: "@cf/moonshotai/kimi-k2.7-code"
    secondary: "@cf/zai-org/glm-5.2"
  max_tokens: 4096
  temperature: 0.3

retry:
  max_retries: 5
  base_delay: 1.0
  max_delay: 60.0

autokeren:
  plan_mode: false
  max_iterations: 25
  shell_timeout: 120
  shell_allowlist: ["node", "npm", "pnpm", "npx", "git", "wrangler", "python3", "pytest"]
  project_root: "."

camofox:
  url: "http://localhost:9377"
  default_profile: "pulsa"
  user_id: "ajat"
```

## Security
- API token stored only in YAML file (0600) and never logged in full.
- Shell commands use allow/blocklist; dangerous commands blocked unless explicitly trusted.
- File writes create `.bak` before overwrite.
- Git working tree checked before auto-commit.

## Roadmap
1. v0.1: chat loop, file/shell/search/web tools, CF AI client, config.
2. v0.2: plan mode, git tool, cost tracking, streaming.
3. v0.3: Camofox e2e tool, Cloudflare deploy tool, tmux supervisor.
4. v0.4: project indexing, retrieval-augmented context, multi-agent kanban.
