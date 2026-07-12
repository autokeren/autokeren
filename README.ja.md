# autokeren

**インタラクティブな TUI を備えた、世界中の開発者のための Cloudflare ファーストの自律型コーディング CLI。**

[English](README.md) | [Bahasa Indonesia](README.id.md) | [简体中文](README.zh-CN.md) | [Português (Brasil)](README.pt-BR.md) | [Español](README.es.md) | **日本語**

`autokeren` は、Cloudflare ファーストの技術スタック向けに特別に設計された自律型（agentic）コーディング CLI です。Python で構築されており、画面を静的なステータスパネルと動的なチャット領域に分割するインタラクティブな **テキストユーザーインターフェイス (TUI)** を提供します。自動フォールバック機能を備えた 7 つの AI モデルをサポートし、ファイル管理、シェル実行、Git 制御、Cloudflare デプロイ、および組み込み PaaS 用のツールを搭載しています。

[![CI](https://github.com/autokeren/autokeren/actions/workflows/ci.yml/badge.svg)](https://github.com/autokeren/autokeren/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/autokeren.svg)](https://pypi.org/project/autokeren/)

![autokeren TUI Screenshot](docs/assets/autogen-ui-preview.jpg)

---

## 主な機能

- **7 つの AI モデル** — kimi-code、kimi-2.6、glm-5.2、glm-flash、llama-4-scout、gemma-4、および nemotron をサポート（自動フォールバック対応）。
- **組み込み PaaS** — ターミナルから直接 Cloudflare Workers にアプリケーションをデプロイし、D1 + R2 + AI バインディングを自動構成。
- **マルチエージェントモードと自動生成** — `/project` を介して複数のエージェントを並行して実行するか、`spawn_agent` ツールを使用してメインエージェントがサブエージェントを動的に呼び出す。
- **MCP サーバーサポート** — Model Context Protocol (MCP) を介してサードパーティの外部ツールを統合し、`/mcp` で管理。
- **入力履歴** — ターミナルで `↑` / `↓` 矢印キーを使用して、以前入力したコマンドをナビゲート。
- **チャットのエクスポート** — `/export` コマンドを使用して、チャット履歴全体を Markdown ファイルとしてエクスポート。
- **ストリーミング出力** — リアルタイムでのトークン単位の応答レンダリング。
- **権限システム** — 危険なシェルコマンドの実行やファイルの変更の前に、確認のプロンプトを表示。
- **クロスセッションメモリ** — 起動時にプロジェクト固有の永続的な記憶を自動的に保存およびロード。
- **セッションの保存と復元 (SQLite)** — 会話状態をトランザクション型ローカル SQLite データベース (`sessions.db`) に保存し、スラッシュコマンドまたは `-r` CLI フラグを使用していつでも復元。
- **コンテキスト追跡 + /compact** — コンテキストウィンドウの使用状況を監視し、履歴を自動または手動で要約。
- **AGENTS.md のサポート** — AI エージェント用のプロジェクト固有の指示ファイルを自動的にロード。
- **Markdown レンダリング** — 見出し、表、およびシンタックスハイライトされたコードブロックの豊富なターミナルフォーマット。
- **KV/D1/PaaS ツール** — エージェントから直接 KV ペアの読み書き、D1 データベースクエリの実行、およびプロジェクトの管理。
- **Tmux スーパーバイザー** — ターミナルが閉じられても存続する、バックグラウンドで実行される長期エージェントを起動および監視。
- **CF Pages/Workers デプロイ** — Cloudflare へのビルドとデプロイのための統合ヘルパーツール。
- **ファイルエクスプローラー (F7)** — TUI 左パネルのフォルダー/ファイルツリーを切り替え、ファイルをクリックすると自動的にその内容を読み取る。

## バイブコーディング（Vibe Coding）機能 (v0.8.0)

他のコーディング CLI（Claude Code、Aider、Cursor、Cline など）にはない 9 つの独自機能：

### タイムトラベル `/rewind`
ツールの呼び出しを取り消し、コードベースを以前のチェックポイントに復元。ファイルを書き込み/修正するたびにチェックポイントが自動的に保存されます。
```bash
/rewind        # 1 つのツール呼び出しを取り消す
/rewind 3      # 3 つのツール呼び出しを取り消す
/rewind list   # 利用可能なすべてのチェックポイントを一覧表示
```

### アーキテクチャの守護者 (Architecture Guardian)
プロジェクトのゲノム（モジュール、関数、依存関係）をインデックス化し、重複する関数/モジュールが書き込まれる前にブロック。
```bash
/genome         # プロジェクトのゲノムを表示
/genome rescan  # プロジェクトのゲノムを再スキャン
/genome check   # 重複する関数をチェック
```

### ループブレイカー (Loop Breaker)
エージェントがエラー/謝罪/ファイルの頻繁な変更などのデッドループに陥っていることを検出。アクティブな AI モデルを自動的に切り替えます。
```bash
/loop status    # ループブレイカーのエラー履歴を表示
/loop reset     # ループトラッカーをリセット
/loop break     # 手動でループを解除 — モデルを切り替え + リセット
```

### クロスモデル自動レビュー (Cross-Model Auto-Review)
ブラインドスポットを捉えるために、別のプロバイダーの AI モデルを使用して未ステージング（unstaged）またはステージング済み（staged）の diff をレビュー。
```bash
/review         # 未ステージの変更をレビュー
/review staged  # ステージ済みの変更をレビュー
```

### セキュリティガード (Vibe-Security Guard)
ファイル書き込みごとに、シークレットの漏洩、SQL インジェクション、XSS、および禁止されたパターンを自動的にスキャン。
```bash
/security           # プロジェクト全体をスキャン
/security app.py    # 特定のファイルをスキャン
```

### リアルタイムのアーキテクチャ強制
`.ak-rules.yaml` の構成に基づくルールの強制（例：ファイルの最大行数、禁止パターン、インポートの制限）。

### スペック駆動自動計画 (Spec-Driven Auto-Planning)
AI がガイドする 20 問の質問を通じて、`plan.md` と `technical-plan.md` を自動的に生成。
```bash
/spec build a REST API     # インタビューを開始
/spec answer 私の回答       # 質問に回答
/spec generate              # 実行計画を生成
/spec show                  # 実行計画を表示
/spec progress              # 実行の進行状況を追跡
```

### ゴーストエージェント (Ghost Agent)
並行タスク実行のために、tmux 内でバックグラウンドエージェントを起動。
```bash
/ghost fix bug in login.py  # ゴーストエージェントを起動
/ghost list                 # すべてのバックグラウンドエージェントを一覧表示
/ghost show 1               # ゴーストエージェント #1 の出力を表示
/ghost kill 1               # ゴーストエージェント #1 を終了
/ghost kill all             # すべてのバックグラウンドエージェントを終了
```

### 調査ツール (Research Tool)
Reddit、Hacker News、および Web 検索をクエリするディープリサーチツール。
```bash
/research python coding tools     # すべてのソースを検索
/research reddit asyncio tips     # Reddit のみ検索
/research hn AI coding CLI        # Hacker News のみ検索
/research web best practices      # 一般 Web のみ検索
```

## AGI 自律進化と自己修復 (v0.11.0+)

自律型人工知能を Autokeren CLI に搭載：

### 1. 継続的なライフサイクルデーモンとオブザーバー
重大なエラーログやファイルの変更を追跡し、自己修復プロセスをトリガーする非同期バックグラウンドシステムオブザーバー (SystemObserver)。

### 2. 自己進化 / 自動リファクタリングループ
破損した Python ツールを自動的にリファクタリングし、新しい pytest 単体テストで検証し、ツールレジストリを動的にリロード（ホットリロード）します。

### 3. ローカル TF-IDF セマンティックメモリ
ローカル SQLite データベース (`memory.db`) 上で、TF-IDF 重み付けとコサイン類似度（Cosine Similarity）を使用したベクトル空間モデル (VSM) による高性能なローカルセマンティック検索。API キーは不要です！

### 4. インタラクティブな看板（Kanban）TUI ボード (`Ctrl+K`)
ターミナル内でプロジェクトのタスクリストを視覚的に管理し、ローカル SQLite とリアルタイム同期。いつでも **`Ctrl+K`** を押して切り替えられます。

### 5. マルチエージェントディベートビュー (`Ctrl+D`)
バックグラウンドのゴーストエージェント (Ghost Agent) の議論、調整、および作業ログをリアルタイムで監視。いつでも **`Ctrl+D`** を押して切り替えられます。

## インストールと設定

### 1. 無料の API キーを取得する

**[developers.autokeren.com](https://developers.autokeren.com)** で登録して API キーを取得します。

### 2. インストール

#### Linux / macOS

```bash
pipx install autokeren
```

> pipx がインストールされていない場合：Linux では `sudo apt install pipx && pipx ensurepath`、macOS では `brew install pipx` を実行してください。
> 代替案：`pip install --user autokeren`

#### Windows (PowerShell)

**ステップ 1** — pip を使用して pipx をインストールします：

```powershell
python -m pip install --user pipx
```

**ステップ 2** — Windows PATH に pipx を追加します：

```powershell
python -m pipx ensurepath
```

**ステップ 3** — PowerShell を再起動します（ターミナルを一度閉じてから再度開きます）。

**ステップ 4** — autokeren をインストールします：

```powershell
pipx install autokeren
```

### 3. ログイン

```bash
autokeren --login
```

developers.autokeren.com から取得した API キーを入力します。

### 4. コーディングを開始する

```bash
autokeren
```

## クイックスタート

### インタラクティブ TUI チャット（デフォルト）

インタラクティブな TUI インターフェイスを起動します：
```bash
autokeren
```

### 単一プロンプト（非インタラクティブ）

```bash
autokeren "create a hello.py file that prints hello world"
```

### 計画モード

```bash
autokeren --plan
```

### 保存されたセッションの復元

ターミナル起動時に直接、保存されたセッションを復元します：
```bash
autokeren --resume セッション名
# または短いフラグを使用
autokeren -r セッション名
```

### モデルの選択

```bash
autokeren -m glm "refactor this function"
autokeren -m kimi "write unit tests for the tools module"
```

### Google AI Studio モード (Gemini API)

独自の Google AI Studio API キーを使用して直接 autokeren を実行します：
```bash
autokeren --aistudio
```
API キーが構成されていない場合、入力を求められます。または、環境変数 `GEMINI_API_KEY` を設定してください。

### アプリケーションのデプロイ

```bash
autokeren "deploy a simple shoe shop with HTML+CSS, using D1 for products"
```

エージェントは自動的にプロジェクトを作成し、コードを記述し、D1 および R2 リソースをバインドして Cloudflare Workers にデプロイします。

## 利用可能なモデル

| エイリアス | モデル |
|---|---|
| `kimi-code` | Moonshot Kimi K2.7-Code (メインモデル) |
| `kimi-2.6` | Moonshot Kimi K2.6 |
| `glm-5.2` | 智譜 GLM 5.2 (サブモデル) |
| `glm-flash` | 智譜 GLM Flash |
| `llama-4-scout` | Meta Llama 4 Scout |
| `gemma-4` | Google Gemma 4 |
| `nemotron` | NVIDIA Nemotron |

AI Studio 専用パス：

| エイリアス | モデル |
|---|---|
| `gemini-3.5-flash` | Google Gemini 3.5 Flash via AI Studio (`--aistudio`) |
| `gemini-3.5-pro` | Google Gemini 3.5 Pro via AI Studio (`--aistudio`) |

`-m <エイリアス>` でモデルを選択。デフォルト：`kimi-code`、回退（fallback）先は `glm-5.2`。

## ショートカットとコマンド

TUI モードでは、次のキーボードショートカットとスラッシュコマンドを使用できます：

### キーボードショートカット (Hotkeys)

| キー | アクション | 説明 |
|---|---|---|
| **`F1`** | ヘルプ | コマンドとショートカットを一覧表示するヘルプダイアログの切り替え |
| **`F2`** | モデル切り替え | インタラクティブなモーダルを開いて AI モデルを切り替える |
| **`F3`** | セッションリセット | 会話履歴とツールの実行権限をリセットする |
| **`F4`** | 回答をコピー | AI の最後の返信メッセージをクリップボードにコピーする |
| **`F5`** | 圧縮 | 現在の会話履歴を圧縮/要約する |
| **`F6`** | 言語切り替え | モーダルを開いて TUI インターフェイス言語を変更する |
| **`F7`** | ファイルツリー | 左パネルのファイルツリーサイドバーの表示/非表示を切り替える |
| **`Ctrl+K`**| 看板パネル | プロジェクトのカンバンボードパネルを切り替える |
| **`Ctrl+D`**| 討論ビュー | マルチエージェントのバックグラウンドディベートビューを切り替える |
| **`Ctrl+C`**| キャンセル / 停止 | 現在の AI 生成または実行中のシェルツールを停止する |
| **`Ctrl+Q`**| 強制終了 | autokeren CLI アプリケーションを強制的に終了する |

### スラッシュコマンド

チャット入力ボックスに直接スラッシュコマンドを入力します（Tab キーによる自動補完に対応）：

| コマンド | 説明 |
|---|---|
| `/help` | ヘルプガイドラインを表示 |
| `/q` または `/quit` | CLI セッションを終了 |
| `/model [name]` | AI モデルを切り替え（名前を省略した場合はポップアップを表示） |
| `/lang [code]` | TUI 言語を切り替え（コードを省略した場合はポップアップを表示、例：`/lang id`） |
| `/export [name]` | 現在の会話を Markdown ファイルにエクスポート |
| `/copy [last\|N]` | 指定したメッセージをクリップボードにコピー |
| `/mcp` | インタラクティブな Model Context Protocol (MCP) 管理画面を開く |
| `/project <サブコマンド>`| マルチエージェントプロジェクト管理コマンド |
| `/compact` | 会話履歴を要約/圧縮 |
| `/reset` | アクティブなセッションをリセット |
| `/memory` | プロジェクト用に保存されたクロスセッションメモリを表示 |
| `/permissions` | 現在付与されているツールの実行権限を表示 |
| `/save [name]` | 現在のセッション状態を保存 |
| `/resume <name\|id>` | 保存されたセッションを復元 |
| `/sessions` | 保存されたすべてのセッションを一覧表示 |
| `/rewind [N]` | N 回のツール呼び出しを取り消し、コードベースをチェックポイントに復元 |
| `/rewind list` | 利用可能なすべてのチェックポイントを一覧表示 |
| `/genome` | プロジェクトの構造ゲノムを表示 |
| `/genome rescan` | プロジェクトの構造ゲノムを再スキャン |
| `/genome check` | 重複する関数をスキャン |
| `/loop status` | ループブレイカーのエラー履歴を表示 |
| `/loop reset` | ループブレイカーの統計情報をリセット |
| `/loop break` | 手動でループを解除（現在のモデルを切り替える） |
| `/review [staged]` | クロスモデルコードレビューを実行 |
| `/security [file]` | 指定したファイルのセキュリティ監査スキャンを実行 |
| `/spec <要求>` | 要件定義インタビューを開始 |
| `/spec answer <回答>` | インタビューの質問への回答を送信 |
| `/spec generate` | plan.md と technical-plan.md を生成 |
| `/spec show` | 実行計画を表示 |
| `/spec progress` | 実行の進行状況を追跡 |
| `/ghost <タスク>` | バックグラウンドでゴーストエージェントを起動 |
| `/ghost list` | バックグラウンドで実行中のすべてのゴーストエージェントを一覧表示 |
| `/ghost show <id>` | 指定したゴーストエージェントのログを表示 |
| `/ghost kill <id\|all>` | 実行中のゴーストエージェントを終了 |
| `/research <検索語>` | Reddit、Hacker News、および Google Web を検索 |
| `/deploy <説明>` | プロジェクトを作成し、直接 Cloudflare Pages/Workers にデプロイ |

## 保存される設定

設定ファイルは `~/.config/autokeren/config.yaml` に保存されます。

```yaml
auth:
  mode: "platform"       # "platform"（デフォルト）、"direct"、または "aistudio"
  api_key: ""            # developers.autokeren.com から取得した API キー
  gemini_api_key: ""     # Google AI Studio API キー（"aistudio" モードのみ）

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
  # Vibe coding 機能
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

### 環境変数

| 変数 | 説明 |
|---|---|
| `AUTOKEREN_API_KEY` | 設定ファイルの API キーを上書きします |
| `GEMINI_API_KEY` | Google AI Studio API キー |
| `AUTOKEREN_CONFIG_DIR` | カスタム設定ディレクトリパス（デフォルト `~/.config/autokeren`） |

## アップグレード更新

最新バージョンにアップグレードするには：
```bash
pipx upgrade autokeren
```

## Go + Python ハイブリッドアーキテクチャ

`autokeren` は、高速な Go インターフェイスドライバーと柔軟な Python AI コアを組み合わせた高性能なハイブリッドアーキテクチャを採用しています：

1.  **フロントエンドと TUI (Go):**
    **Bubble Tea** と **Lip Gloss** を使用して構築。レイアウト構造、ファイルツリーナビゲーション、入力コマンド履歴、看板ボード、マルチエージェントディベートビューを管理し、Go-Rod ブラウザ自動化子プロセスを制御します。
2.  **AI コアと頭脳 (Python):**
    マルチターンエージェントループ、マルチモデル代替ルーティング、静的解析（AST 解析）、およびセキュリティスキャンを管理します。
3.  **IPC 通信 (Inter-Process Communication):**
    動的かつランダムなローカルポート上で、**Local TCP Socket** を介して非同期の **JSON-RPC 2.0** 接続を確立します。
    
    *なぜ Local TCP Socket なのか？*
    これにより、JSON-RPC データパケットが Python プロセスの標準出力 (stdout) ストリームから隔離されます。依存関係パッケージが誤って出力するログ (`print()`) や警告情報はすべてバックグラウンドの stderr にリダイレクトされ、パーサーのクラッシュや TUI インターフェイスのフリーズバグが解消されます。

## 貢献ガイドライン

コミュニティへの貢献を歓迎します！リポジトリをフォークし、機能ブランチを作成して、PR を送信してください。

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

コードを送信する前に、`ruff check .`、`mypy autokeren`、および `pytest` がすべて合格することを確認してください。

## ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています。詳細については、[LICENSE](LICENSE) ファイルを参照してください。

## 免責事項

autokeren は独立したプロジェクトであり、**Cloudflare, Inc. との提携、承認、または後援はありません。** "Cloudflare" および関連する製品名は Cloudflare, Inc. の登録商標です。autokeren は、サードパーティのクライアントとして公開されている Cloudflare API と Workers インフラストラクチャを使用します。
