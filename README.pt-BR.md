# autokeren

**CLI de codificação agentic focado em Cloudflare com uma TUI interativa para desenvolvedores do mundo todo.**

[English](README.md) | [Bahasa Indonesia](README.id.md) | [简体中文](README.zh-CN.md) | **Português (Brasil)** | [Español](README.es.md) | [日本語](README.ja.md)

`autokeren` é um CLI de codificação agentic projetado especificamente para a stack do Cloudflare. Desenvolvido com Python, o `autokeren` oferece uma **Interface de Usuário de Texto (TUI) interativa** que divide a tela em um painel de status estático e uma área de chat dinâmica. Ele suporta 7 modelos de IA com fallback automático e vem equipado com ferramentas integradas para gerenciamento de arquivos, execução no shell, controle de git, deploy no Cloudflare e um PaaS embutido.

[![CI](https://github.com/autokeren/autokeren/actions/workflows/ci.yml/badge.svg)](https://github.com/autokeren/autokeren/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/autokeren.svg)](https://pypi.org/project/autokeren/)

![autokeren TUI Screenshot](docs/assets/autogen-ui-preview.jpg)

---

## Principais Recursos

- **7 Modelos de IA** — kimi-code, kimi-2.6, glm-5.2, glm-flash, llama-4-scout, gemma-4 e nemotron com fallback automático.
- **PaaS Embutido** — faça o deploy de aplicações para o Cloudflare Workers diretamente do terminal, com bindings automáticos de D1 + R2 + AI.
- **Modo Multi-Agent & Auto Spawn** — execute múltiplos agentes em paralelo via `/project` ou permita que o agente principal chame subagentes dinamicamente usando a ferramenta `spawn_agent`.
- **Suporte ao Servidor MCP** — integre ferramentas externas de terceiros por meio do Model Context Protocol (MCP) e gerencie-as via `/mcp`.
- **Histórico de Entrada** — navegue pelas entradas de comandos anteriores usando as teclas de seta `↑` / `↓` no terminal.
- **Exportar Chat** — exporte todo o histórico do chat como um arquivo Markdown usando o comando `/export`.
- **Saída em Tempo Real (Streaming)** — renderização de resposta token por token em tempo real.
- **Sistema de Permissões** — solicita confirmação antes de executar comandos perigosos no shell ou modificar arquivos.
- **Memória entre Sessões** — armazena e carrega automaticamente a memória persistente específica do projeto ao iniciar.
- **Salvar/Retomar Sessão (SQLite)** — salve o estado da conversa em um banco de dados SQLite local transacional (`sessions.db`) e retome a qualquer momento usando comandos slash ou a flag `-r`.
- **Acompanhamento de Contexto + /compact** — monitore o uso da janela de contexto e resuma o histórico de forma automática ou manual.
- **Suporte ao AGENTS.md** — carrega automaticamente as instruções específicas do projeto para o agente de IA.
- **Renderização Markdown** — formatação rica no terminal para títulos, tabelas e blocos de código com destaque de sintaxe.
- **Ferramentas de KV/D1/PaaS** — leia/escreva pares de KV, execute queries no banco de dados D1 e gerencie projetos diretamente a partir do agente.
- **Supervisor Tmux** — crie e monitore agentes em segundo plano que sobrevivem ao fechamento do terminal.
- **Deploy no CF Pages/Workers** — ferramentas integradas para build e deploy no Cloudflare.
- **File Explorer (F7)** — alterne a árvore de pastas/arquivos no painel esquerdo da TUI, clique em um arquivo para ler seu conteúdo automaticamente.

## Recursos de Vibe Coding (v0.8.0)

9 recursos originais não encontrados em outros CLIs de codificação (Claude Code, Aider, Cursor, Cline):

### Viagem no Tempo `/rewind`
Desfaça chamadas de ferramentas e restaure a base de código para checkpoints anteriores. Salva automaticamente um checkpoint após cada escrita/patch de arquivo.
```bash
/rewind        # desfaz 1 chamada de ferramenta
/rewind 3      # desfaz 3 chamadas de ferramenta
/rewind list   # lista todos os checkpoints disponíveis
```

### Guardião de Arquitetura (Architecture Guardian)
Indexa o genoma do projeto (módulos, funções, dependências) e bloqueia funções/módulos duplicados antes que sejam escritos.
```bash
/genome         # exibe o genoma do projeto
/genome rescan  # varre novamente o genoma do projeto
/genome check   # verifica se há funções duplicadas
```

### Loop Breaker
Detecta quando o agente está preso em um loop de erro/desculpas/modificações frequentes de arquivo. Altera automaticamente o modelo de IA ativo.
```bash
/loop status    # exibe o histórico de erros do loop breaker
/loop reset     # reseta o rastreador de loop
/loop break     # quebra o loop manualmente — altera o modelo + reseta
```

### Auto-Revisão entre Modelos (Cross-Model Auto-Review)
Revisa diffs unstaged ou staged usando um modelo de IA de outro provedor para identificar pontos cegos.
```bash
/review         # revisa as alterações não preparadas (unstaged)
/review staged  # revisa as alterações preparadas (staged)
```

### Guarda de Segurança (Vibe-Security Guard)
Varre automaticamente cada escrita de arquivo em busca de segredos vazados, SQL injection, XSS e padrões proibidos.
```bash
/security           # varre todo o projeto
/security app.py    # varre um arquivo específico
```

### Execução de Arquitetura em Tempo Real
Aplicação de regras com base em configuração no arquivo `.ak-rules.yaml` (ex: limite de linhas por arquivo, padrões proibidos, restrições de imports).

### Planejamento Automático Orientado a Specs (Spec-Driven Auto-Planning)
Entrevista guiada por IA com 20 perguntas para gerar automaticamente `plan.md` e `technical-plan.md`.
```bash
/spec build a REST API     # inicia a entrevista
/spec answer minha resposta # responde a perguntas da entrevista
/spec generate              # gera o plano de execução
/spec show                  # visualiza o plano de execução
/spec progress              # acompanha o progresso do plano
```

### Agente Fantasma (Ghost Agent)
Inicia agentes em segundo plano no tmux para execução paralela de tarefas.
```bash
/ghost fix bug in login.py  # inicia um agente fantasma
/ghost list                 # lista todos os agentes fantasma ativos
/ghost show 1               # exibe a saída do agente fantasma #1
/ghost kill 1               # encerra o agente fantasma #1
/ghost kill all             # encerra todos os agentes fantasma
```

### Ferramenta de Pesquisa (Research Tool)
Pesquisa profunda na web consultando Reddit, Hacker News e mecanismos de busca na web.
```bash
/research python coding tools     # pesquisa em todas as fontes
/research reddit asyncio tips     # pesquisa apenas no Reddit
/research hn AI coding CLI        # pesquisa apenas no Hacker News
/research web best practices      # pesquisa apenas na web geral
```

## Evolução e Autocorreção de AGI (v0.11.0+)

Trazendo recursos de inteligência artificial autônoma para o Autokeren CLI:

### 1. Daemon e Observador de Ciclo de Vida Contínuo
Um observador de sistema assíncrono em segundo plano (SystemObserver) monitorando logs de erro críticos e alterações de arquivos para acionar processos de autocorreção.

### 2. Ciclo de Autoevolução / Auto-Refatoração
Refatora automaticamente ferramentas Python quebradas, valida-as com novos testes unitários do pytest e recarrega dinamicamente o registro de ferramentas (hot-reload).

### 3. Memória Semântica Local TF-IDF
Busca semântica de alta performance local usando Vector Space Model (VSM) com pesos TF-IDF e Cosine Similarity em um banco de dados SQLite local (`memory.db`). Sem necessidade de chaves de API!

### 4. Painel Kanban TUI Interativo (`Ctrl+K`)
Gerencie listas de tarefas de projetos visualmente no terminal, sincronizado com o SQLite local. Pressione **`Ctrl+K`** para alternar a qualquer momento.

### 5. Visualização de Debate Multi-Agent (`Ctrl+D`)
Monitore discussões, coordenação e logs de trabalho dos Agentes Fantasma (Ghost Agents) em segundo plano em tempo real. Pressione **`Ctrl+D`** para alternar a visualização.

## Instalação e Configuração

### 1. Obtenha uma chave de API gratuita

Cadastre-se em **[developers.autokeren.com](https://developers.autokeren.com)** para obter sua chave de API.

### 2. Instalação

#### Linux / macOS

```bash
pipx install autokeren
```

> Se você não tiver o pipx: `sudo apt install pipx && pipx ensurepath` (Linux) ou `brew install pipx` (macOS)
> Alternativa: `pip install --user autokeren`

#### Windows (PowerShell)

**Passo 1** — Instale o pipx via pip:

```powershell
python -m pip install --user pipx
```

**Passo 2** — Adicione o pipx ao PATH do Windows:

```powershell
python -m pipx ensurepath
```

**Passo 3** — Reinicie o PowerShell (feche e abra o terminal novamente).

**Passo 4** — Instale o autokeren:

```powershell
pipx install autokeren
```

### 3. Login

```bash
autokeren --login
```

Insira sua chave de API obtida em developers.autokeren.com.

### 4. Comece a Codar

```bash
autokeren
```

## Guia de Início Rápido

### Chat TUI Interativo (Padrão)

Abra a interface TUI interativa:
```bash
autokeren
```

### Prompt Único (Não interativo)

```bash
autokeren "create a hello.py file that prints hello world"
```

### Modo de Planejamento (Plan Mode)

```bash
autokeren --plan
```

### Retomar Sessão Salva

Retome uma sessão salva diretamente na inicialização do terminal:
```bash
autokeren --resume nome-da-sessao
# ou usando a flag curta
autokeren -r nome-da-sessao
```

### Escolher Modelo de IA

```bash
autokeren -m glm "refactor this function"
autokeren -m kimi "write unit tests for the tools module"
```

### Modo Google AI Studio (Gemini API)

Execute o autokeren diretamente usando sua própria chave de API do Google AI Studio:
```bash
autokeren --aistudio
```
Se a chave de API não estiver configurada, você será solicitado a inseri-la. Alternativamente, defina a variável de ambiente `GEMINI_API_KEY`.

### Deploy de Aplicação

```bash
autokeren "deploy a simple shoe shop with HTML+CSS, using D1 for products"
```

O agente criará o projeto automaticamente, escreverá o código e fará o deploy no Cloudflare Workers com bindings para D1 e R2.

## Modelos Disponíveis

| Alias | Modelo |
|---|---|
| `kimi-code` | Moonshot Kimi K2.7-Code (principal) |
| `kimi-2.6` | Moonshot Kimi K2.6 |
| `glm-5.2` | Zai GLM 5.2 (secundário) |
| `glm-flash` | Zai GLM Flash |
| `llama-4-scout` | Meta Llama 4 Scout |
| `gemma-4` | Google Gemma 4 |
| `nemotron` | NVIDIA Nemotron |

Caminhos do AI Studio:

| Alias | Modelo |
|---|---|
| `gemini-3.5-flash` | Google Gemini 3.5 Flash via AI Studio (`--aistudio`) |
| `gemini-3.5-pro` | Google Gemini 3.5 Pro via AI Studio (`--aistudio`) |

Selecione um modelo com `-m <alias>`. Padrão: `kimi-code` com fallback para `glm-5.2`.

## Comandos e Atalhos

Use os seguintes atalhos de teclado e comandos slash no modo TUI:

### Atalhos de Teclado (Hotkeys)

| Tecla | Ação | Descrição |
|---|---|---|
| **`F1`** | Ajuda | Abre o diálogo de ajuda listando comandos e atalhos |
| **`F2`** | Alterar Modelo | Abre um modal interativo para mudar de modelo de IA |
| **`F3`** | Reiniciar Sessão | Reseta o histórico de conversas e as permissões de ferramentas |
| **`F4`** | Copiar Resposta | Copia a última mensagem de resposta da IA para a área de transferência |
| **`F5`** | Compactar | Resume/compacta o histórico da conversa |
| **`F6`** | Alterar Idioma | Abre um modal para mudar o idioma da interface TUI |
| **`F7`** | File Explorer | Alterna a exibição da árvore de arquivos no painel esquerdo |
| **`Ctrl+K`**| Painel Kanban | Alterna o painel do quadro Kanban do projeto |
| **`Ctrl+D`**| Debate Multi-Agent | Alterna a visualização de debate de agentes em segundo plano |
| **`Ctrl+C`**| Cancelar / Parar | Interrompe a geração ativa de IA ou ferramenta de shell em execução |
| **`Ctrl+Q`**| Forçar Saída | Fecha imediatamente o CLI do autokeren |

### Comandos Slash

Digite comandos slash diretamente na caixa de entrada do chat (suporta autocompletar com Tab):

| Comando | Descrição |
|---|---|
| `/help` | Exibe diretrizes de ajuda |
| `/q` ou `/quit` | Encerra a sessão do CLI |
| `/model [nome]` | Altera o modelo de IA (abre pop-up se o nome for omitido) |
| `/lang [codigo]` | Altera o idioma da TUI (abre pop-up se o código for omitido, ex: `/lang id`) |
| `/export [nome]` | Exporta a conversa ativa para um arquivo Markdown |
| `/copy [last\|N]` | Copia uma mensagem específica para a área de transferência |
| `/mcp` | Abre o gerenciador interaktif do servidor Model Context Protocol (MCP) |
| `/project <subcomando>`| Comando de gerenciamento de projeto multi-agent |
| `/compact` | Compacta o histórico da conversa |
| `/reset` | Reseta a sessão ativa |
| `/memory` | Exibe a memória entre sessões salva para o projeto |
| `/permissions` | Exibe as permissões atuais concedidas para execução de ferramentas |
| `/save [nome]` | Salva o estado da sessão atual |
| `/resume <nome\|id>` | Retoma uma sessão salva |
| `/sessions` | Lista todas as sessões salvas |
| `/rewind [N]` | Desfaz N chamadas de ferramentas e restaura a base de código |
| `/rewind list` | Lista todos os checkpoints disponíveis |
| `/genome` | Exibe o genoma estrutural do projeto |
| `/genome rescan` | Varre novamente o genoma de arquitetura do projeto |
| `/genome check` | Verifica se há funções duplicadas |
| `/loop status` | Exibe o histórico de erros do loop breaker |
| `/loop reset` | Reseta as estatísticas do loop breaker |
| `/loop break` | Quebra o loop manualmente (altera o modelo ativo) |
| `/review [staged]` | Executa a revisão de código cruzada entre modelos |
| `/security [file]` | Executa auditoria de segurança em um arquivo |
| `/spec <requisito>` | Inicia a entrevista de levantamento de requisitos |
| `/spec answer <texto>` | Envia resposta para a pergunta da entrevista |
| `/spec generate` | Gera os arquivos plan.md e technical-plan.md |
| `/spec show` | Exibe o plano de execução |
| `/spec progress` | Acompanha o progresso da execução |
| `/ghost <tarefa>` | Inicia um agente fantasma em segundo plano |
| `/ghost list` | Lista todos os agentes fantasma em execução no background |
| `/ghost show <id>` | Exibe logs de um agente fantasma específico |
| `/ghost kill <id\|all>` | Encerra os agentes fantasma em execução |
| `/research <query>` | Pesquisa no Reddit, Hacker News e motores de busca da web |
| `/deploy <desc>` | Cria o projeto e faz deploy direto no Cloudflare Pages/Workers |

## Configurações Salvas

O arquivo de configuração fica em `~/.config/autokeren/config.yaml`.

```yaml
auth:
  mode: "platform"       # "platform" (padrão), "direct" ou "aistudio"
  api_key: ""            # Chave de API de developers.autokeren.com
  gemini_api_key: ""     # Chave de API do Google AI Studio (apenas para o modo "aistudio")

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
  # Recursos de Vibe coding
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

### Variáveis de Ambiente

| Variável | Descrição |
|---|---|
| `AUTOKEREN_API_KEY` | Substitui a chave de API da configuração |
| `GEMINI_API_KEY` | Chave de API do Google AI Studio |
| `AUTOKEREN_CONFIG_DIR` | Diretório de configuração customizado (padrão `~/.config/autokeren`) |

## Atualização

Para atualizar para a versão mais recente:
```bash
pipx upgrade autokeren
```

## Arquitetura Hybrid Go + Python

O `autokeren` utiliza uma arquitetura híbrida de alto desempenho que combina um driver Go para a interface com um núcleo em Python para a inteligência artificial:

1.  **Frontend & TUI (Go):**
    Construído usando os frameworks **Bubble Tea** e **Lip Gloss**. Gerencia o layout, árvore de arquivos, histórico de comandos, Kanban, debate de agentes e controla os processos do navegador Go-Rod.
2.  **AI Core & Brain (Python):**
    Gerencia o ciclo agentic multi-turn, roteamento de fallback multi-model, análise estática (AST parsing) e verificação de segurança.
3.  **IPC (Inter-Process Communication):**
    Conexão assíncrona **JSON-RPC 2.0** estabelecida através de um **Socket TCP Local** em uma porta dinâmica.
    
    *Por que um Socket TCP Local?*
    Isso separa os pacotes de dados do JSON-RPC do fluxo de saída padrão (stdout) do processo Python. Quaisquer logs acidentais (`print()`) ou warnings de dependências são redirecionados para o stderr do background, evitando crashes de parser e congelamentos da TUI (*TUI freeze*).

## Contribuição

Contribuições são bem-vindas! Crie um fork do repositório, crie uma feature branch e envie seu PR.

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Antes de enviar código, certifique-se de que os testes `ruff check .`, `mypy autokeren` e `pytest` passem com sucesso.

## Licença

Este projeto é licenciado sob a licença MIT - consulte o arquivo [LICENSE](LICENSE) para obter detalhes.

## Disclaimer

autokeren é um projeto independente e **não é afiliado, endossado ou patrocinado pela Cloudflare, Inc.** "Cloudflare" e os nomes de produtos associados são marcas registradas da Cloudflare, Inc. O autokeren usa APIs públicas do Cloudflare e infraestrutura de Workers como um cliente de terceiros.
