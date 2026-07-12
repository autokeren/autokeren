# autokeren

**基于 Cloudflare 的 Agentic 编程 CLI，配有面向全球开发者的交互式 TUI。**

[English](README.md) | [Bahasa Indonesia](README.id.md) | **简体中文** | [Português (Brasil)](README.pt-BR.md) | [Español](README.es.md) | [日本語](README.ja.md)

`autokeren` 是一款专为 Cloudflare 栈设计的 agentic 编程 CLI。它基于 Python 开发，提供交互式**文本用户界面 (TUI)**，将屏幕分割为静态状态面板和动态聊天区域。它支持 7 种 AI 模型并具备自动回退（fallback）机制，内置文件管理、终端执行、git 控制、Cloudflare 部署以及内置 PaaS 工具。

[![CI](https://github.com/autokeren/autokeren/actions/workflows/ci.yml/badge.svg)](https://github.com/autokeren/autokeren/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/autokeren.svg)](https://pypi.org/project/autokeren/)

![autokeren TUI Screenshot](docs/assets/autogen-ui-preview.jpg)

---

## 核心功能

- **7 种 AI 模型** — kimi-code, kimi-2.6, glm-5.2, glm-flash, llama-4-scout, gemma-4, 以及 nemotron，具备自动回退机制。
- **内置 PaaS** — 直接从终端部署应用到 Cloudflare Workers，自动配置 D1 + R2 + AI 绑定。
- **多智能体模式与自动生成 (Multi-Agent & Auto Spawn)** — 通过 `/project` 并行运行多个 Agent，或允许主 Agent 使用 `spawn_agent` 工具动态调用子 Agent。
- **MCP 服务支持** — 通过 Model Context Protocol (MCP) 集成第三方外部工具，并通过 `/mcp` 进行管理。
- **输入历史** — 在终端中使用 `↑` / `↓` 方向键浏览以前输入的命令。
- **导出聊天** — 使用 `/export` 命令将整个聊天历史记录导出为 Markdown 文件。
- **流式输出** — 实时进行 Token 级别的响应渲染。
- **权限系统** — 在执行具有潜在危险的 Shell 命令或修改文件之前提示用户确认。
- **跨会话记忆** — 启动时自动存储和加载项目专有的持久记忆。
- **会话保存与恢复 (SQLite)** — 将会话状态保存到事务型本地 SQLite 数据库 (`sessions.db`) 中，并可随时使用斜杠命令或 `-r` CLI 标志恢复。
- **上下文跟踪 + /compact** — 监控上下文窗口使用情况，自动或手动压缩历史记录。
- **AGENTS.md 支持** — 自动加载项目专有的 AI Agent 提示指令。
- **Markdown 渲染** — 终端富文本格式化，支持标题、表格和语法高亮的代码块。
- **KV/D1/PaaS 工具** — 直接在 Agent 中读写 KV 键值对、运行 D1 数据库查询并管理项目。
- **Tmux 监督器** — 启动并监控在后台运行的、在终端关闭后仍能存活的长时运行 Agent。
- **CF Pages/Workers 部署** — 集成了用于构建和部署到 Cloudflare 的辅助工具。
- **文件浏览器 (F7)** — 切换 TUI 左侧面板的文件夹/文件树，点击文件可自动读取其内容。

## Vibe Coding 专属功能 (v0.8.0)

9 种在其他编程 CLI（如 Claude Code, Aider, Cursor, Cline）中未见的原创功能：

### 时空穿梭 `/rewind`
撤销工具调用并将代码库恢复到以前的检查点。每次文件写入/修补后都会自动保存检查点。
```bash
/rewind        # 撤销 1 次工具调用
/rewind 3      # 撤销 3 次工具调用
/rewind list   # 列出所有可用的检查点
```

### 架构守护者 (Architecture Guardian)
索引项目基因组（模块、函数、依赖关系），并在写入前阻止重复的函数/模块。
```bash
/genome         # 查看项目基因组
/genome rescan  # 重新扫描项目基因组
/genome check   # 检查重复函数
```

### 循环破坏者 (Loop Breaker)
检测 Agent 是否陷入错误/道歉/文件剧烈变动等死循环。自动切换当前的 AI 模型。
```bash
/loop status    # 查看循环破坏者错误历史
/loop reset     # 重置循环追踪器
/loop break     # 手动打破循环 — 切换模型 + 重置
```

### 跨模型自动评审 (Cross-Model Auto-Review)
使用来自不同服务商的 AI 模型审查未暂存（unstaged）或已暂存（staged）的 diff，以捕获盲点。
```bash
/review         # 审查未暂存的差异
/review staged  # 审查已暂存的差异
```

### 安全卫士 (Vibe-Security Guard)
自动扫描每次文件写入，检测密钥泄漏、SQL 注入、XSS 和禁用模式。
```bash
/security           # 扫描整个项目
/security app.py    # 扫描指定文件
```

### 动态架构强制执行 (Live Architecture Enforcement)
基于规则的强制执行，通过 `.ak-rules.yaml` 配置（例如：最大文件行数、禁用模式、导入限制）。

### 需求驱动自动规划 (Spec-Driven Auto-Planning)
AI 引导的 20 问用户访谈，自动生成 `plan.md` 和 `technical-plan.md`。
```bash
/spec build a REST API     # 开始访谈
/spec answer my answer     # 回答访谈问题
/spec generate              # 生成执行计划
/spec show                  # 查看执行计划
/spec progress              # 追踪执行进度
```

### 幽灵智能体 (Ghost Agent)
在 tmux 中启动后台 Agent 以并行执行任务。
```bash
/ghost fix bug in login.py  # 启动幽灵智能体
/ghost list                 # 列出所有后台幽灵智能体
/ghost show 1               # 查看幽灵智能体 #1 的输出
/ghost kill 1               # 杀死幽灵智能体 #1
/ghost kill all             # 杀死所有后台幽灵智能体
```

### Riset Riset riset 深度研究工具
深入 Reddit、Hacker News 以及谷歌网页搜索的深度研究工具。
```bash
/research python coding tools     # 搜索所有来源
/research reddit asyncio tips     # 仅搜索 Reddit
/research hn AI coding CLI        # 仅搜索 Hacker News
/research web best practices      # 仅搜索谷歌网页
```

## AGI 自主进化与自愈 (v0.11.0+)

为 Autokeren CLI 带来完全自主的 AI 能力：

### 1. 持续生命周期守护进程与观察者 (SystemObserver)
一个异步的后台系统观察者，追踪关键错误日志和文件更改，以触发自愈流程。

### 2. 自主进化与自动重构循环
自动重构损坏的 Python 工具，使用新的 pytest 单元测试进行验证，并热加载（hot-reload）工具注册表。

### 3. 本地 TF-IDF 语义记忆
使用基于 SQLite 数据库 (`memory.db`) 上的向量空间模型（VSM）、TF-IDF 权重和余弦相似度（Cosine Similarity），在本地实现高性能的语义搜索。无需 API Key！

### 4. 交互式看板 TUI 面板 (`Ctrl+K`)
直接在终端中可视化管理项目任务列表，与本地 SQLite 实时同步。随时按下 **`Ctrl+K`** 即可切换看板。

### 5. 多智能体实时辩论视图 (`Ctrl+D`)
实时监控后台多个幽灵智能体（Ghost Agent）的讨论、协调和工作日志。随时按下 **`Ctrl+D`** 即可切换辩论视图。

## 安装与设置

### 1. 获取免费 API Key

在 **[developers.autokeren.com](https://developers.autokeren.com)** 注册以获取您的 API key。

### 2. 安装

#### Linux / macOS

```bash
pipx install autokeren
```

> 如果您尚未安装 pipx：在 Linux 上运行 `sudo apt install pipx && pipx ensurepath`；在 macOS 上运行 `brew install pipx`。
> 替代方案：`pip install --user autokeren`

#### Windows (PowerShell)

**第一步** — 通过 pip 安装 pipx：

```powershell
python -m pip install --user pipx
```

**第二步** — 将 pipx 添加到 Windows PATH：

```powershell
python -m pipx ensurepath
```

**第三步** — 重启 PowerShell（关闭并重新打开终端）。

**第四步** — 安装 autokeren：

```powershell
pipx install autokeren
```

### 3. 登录

```bash
autokeren --login
```

输入来自 developers.autokeren.com 的 API key。

### 4. 开始编程

```bash
autokeren
```

## 快速上手

### 交互式 TUI 聊天（默认）

启动交互式 TUI 界面：
```bash
autokeren
```

### 单次提示词（非交互式）

```bash
autokeren "create a hello.py file that prints hello world"
```

### 规划模式

```bash
autokeren --plan
```

### 恢复已保存的会话

直接从终端启动时恢复已保存的会话：
```bash
autokeren --resume my-session-name
# 或使用简短标志
autokeren -r my-session-name
```

### 选择模型

```bash
autokeren -m glm "refactor this function"
autokeren -m kimi "write unit tests for the tools module"
```

### Google AI Studio 模式 (Gemini API)

直接使用您自己的 Google AI Studio API key 运行 autokeren：
```bash
autokeren --aistudio
```
如果未配置 API key，系统会提示您输入。或者，也可以设置 `GEMINI_API_KEY` 环境变量。

### 部署应用

```bash
autokeren "deploy a simple shoe shop with HTML+CSS, using D1 for products"
```

Agent 将自动创建项目、编写代码，并部署到绑定了 D1 和 R2 资源的 Cloudflare Workers。

## 可用模型

| 别名 | 模型 |
|---|---|
| `kimi-code` | Moonshot Kimi K2.7-Code (主模型) |
| `kimi-2.6` | Moonshot Kimi K2.6 |
| `glm-5.2` | 智谱 GLM 5.2 (辅模型) |
| `glm-flash` | 智谱 GLM Flash |
| `llama-4-scout` | Meta Llama 4 Scout |
| `gemma-4` | Google Gemma 4 |
| `nemotron` | NVIDIA Nemotron |

AI Studio 专有路径：

| 别名 | 模型 |
|---|---|
| `gemini-3.5-flash` | Google Gemini 3.5 Flash via AI Studio (`--aistudio`) |
| `gemini-3.5-pro` | Google Gemini 3.5 Pro via AI Studio (`--aistudio`) |

使用 `-m <别名>` 选择模型。默认：`kimi-code`，回退（fallback）至 `glm-5.2`。

## 快捷键与命令

在 TUI 模式下可使用以下键盘快捷键和斜杠命令：

### 键盘快捷键 (Hotkeys)

| 按键 | 动作 | 描述 |
|---|---|---|
| **`F1`** | 帮助 | 切换帮助对话框，列出命令和快捷键 |
| **`F2`** | 切换模型 | 打开交互式模态弹窗切换 AI 模型 |
| **`F3`** | 重置会话 | 重置会话历史和工具授权许可 |
| **`F4`** | 复制回复 | 将 AI 的最后一条回复消息复制到剪贴板 |
| **`F5`** | 压缩 | 压缩/总结当前的会话历史记录 |
| **`F6`** | 切换语言 | 打开模态弹窗以更改 TUI 界面语言 |
| **`F7`** | 文件浏览器 | 切换左侧面板的文件树侧边栏 |
| **`Ctrl+K`**| 看板面板 | 切换项目看板面板 |
| **`Ctrl+D`**| 辩论视图 | 切换多智能体后台辩论视图 |
| **`Ctrl+C`**| 取消 / 停止 | 停止当前 AI 生成或正在运行的 Shell 工具 |
| **`Ctrl+Q`**| 强制退出 | 强制退出 autokeren CLI 应用程序 |

### 斜杠命令

直接在聊天输入框中输入斜杠命令（支持 Tab 键自动补全）：

| 命令 | 描述 |
|---|---|
| `/help` | 显示帮助指南 |
| `/q` 或 `/quit` | 退出 CLI 会话 |
| `/model [name]` | 切换 AI 模型（若省略名称则打开弹窗） |
| `/lang [code]` | 切换 TUI 语言（若省略代码则打开弹窗，例如：`/lang id`） |
| `/export [name]` | 将会话导出为 Markdown 文件 |
| `/copy [last\|N]` | 复制指定消息到剪贴板 |
| `/mcp` | 打开交互式 Model Context Protocol (MCP) 服务管理器 |
| `/project <子命令>`| 多智能体项目管理命令 |
| `/compact` | 压缩会话历史 |
| `/reset` | 重置当前会话状态 |
| `/memory` | 查看项目存储的跨会话记忆 |
| `/permissions` | 查看当前已授予的工具执行权限 |
| `/save [name]` | 保存当前的会话状态 |
| `/resume <name\|id>` | 恢复已保存的会话 |
| `/sessions` | 列出所有已保存的会话 |
| `/rewind [N]` | 撤销 N 次工具调用并将代码库恢复到检查点 |
| `/rewind list` | 列出所有可用的检查点 |
| `/genome` | 查看项目结构基因组 |
| `/genome rescan` | 重新扫描项目结构基因组 |
| `/genome check` | 扫描重复函数 |
| `/loop status` | 查看循环破坏者错误历史 |
| `/loop reset` | 重置循环破坏者统计数据 |
| `/loop break` | 手动打破循环（切换当前活跃模型） |
| `/review [staged]` | 运行跨模型代码评审 |
| `/security [file]` | 对指定文件运行安全审计扫描 |
| `/spec <需求>` | 开启需求收集访谈 |
| `/spec answer <回答>` | 提交对访谈问题的回答 |
| `/spec generate` | 生成 plan.md 和 technical-plan.md |
| `/spec show` | 查看执行计划 |
| `/spec progress` | 追踪执行进度 |
| `/ghost <任务>` | 启动后台幽灵智能体 |
| `/ghost list` | 列出所有正在运行的后台幽灵智能体 |
| `/ghost show <id>` | 查看指定后台幽灵智能体的日志 |
| `/ghost kill <id\|all>` | 终止后台幽灵智能体 |
| `/research <查询>` | 搜索 Reddit、Hacker News 和谷歌网页 |
| `/deploy <描述>` | 创建项目并直接部署到 Cloudflare Pages/Workers |

## 配置文件结构

配置文件存储在 `~/.config/autokeren/config.yaml`。

```yaml
auth:
  mode: "platform"       # "platform"（默认），"direct" 或 "aistudio"
  api_key: ""            # 来自 developers.autokeren.com 的 API key
  gemini_api_key: ""     # Google AI Studio API key（仅适用于 "aistudio" 模式）

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
  # Vibe coding 功能
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

### 环境变量

| 变量 | 描述 |
|---|---|
| `AUTOKEREN_API_KEY` | 覆盖配置的 API key |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `AUTOKEREN_CONFIG_DIR` | 自定义配置目录路径（默认 `~/.config/autokeren`） |

## 升级更新

升级到最新版本：
```bash
pipx upgrade autokeren
```

## Go + Python 混合架构

`autokeren` 采用了高性能的混合架构，将高效的 Go 界面驱动器与灵活的 Python AI 核心相结合：

1.  **前端与 TUI (Go):**
    基于 **Bubble Tea** 和 **Lip Gloss** 构建。管理布局结构、文件树导航、输入命令历史记录、看面板、多智能体辩论视图，并控制 Go-Rod 浏览器自动化子进程。
2.  **核心 AI 与大脑 (Python):**
    管理多轮 Agentic 循环、多模型备用路由、静态分析（AST 解析）和安全防护扫描。
3.  **IPC 通信 (Inter-Process Communication):**
    在动态随机本地端口上通过 **Local TCP Socket** 建立异步的 **JSON-RPC 2.0** 连接。
    
    *为什么选择 Local TCP Socket？*
    这样能将 JSON-RPC 数据包与 Python 进程的标准输出 (stdout) 流隔离开来。任何依赖包意外打印的日志 (`print()`) 或警告信息都将被直接重定向到后台的 stderr 中，从而消除了解析器崩溃和 TUI 界面冻结的 bug。

## 贡献指南

欢迎贡献！请 Fork 仓库，创建功能分支，并提交 PR。

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

在提交代码前，请确保 `ruff check .`, `mypy autokeren`, 和 `pytest` 均顺利运行并通过。

## 开源协议

本项目采用 MIT 开源协议 - 详情请参阅 [LICENSE](LICENSE) 文件。

## 免责声明

autokeren 是一个独立的项目，**不隶属于 Cloudflare, Inc.，也未获得其授权或赞助。** "Cloudflare" 及相关产品名称是 Cloudflare, Inc. 的注册商标。autokeren 使用公开的 Cloudflare API 和 Workers 基础设施作为第三方客户端。
