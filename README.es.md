# autokeren

**CLI de codificación agentic centrado en Cloudflare con una TUI interactiva para desarrolladores de todo el mundo.**

[English](README.md) | [Bahasa Indonesia](README.id.md) | [简体中文](README.zh-CN.md) | [Português (Brasil)](README.pt-BR.md) | **Español** | [日本語](README.ja.md)

`autokeren` es un CLI de codificación agentic diseñado específicamente para el stack de Cloudflare. Desarrollado con Python, `autokeren` ofrece una **interfaz de usuario de texto (TUI) interactiva** que divide la pantalla en un panel de estado estático y una zona de chat dinámica. Soporta 7 modelos de IA con fallback automático y está equipado con herramientas integradas para la gestión de archivos, ejecución de terminal, control de git, despliegue en Cloudflare y un PaaS integrado.

[![CI](https://github.com/autokeren/autokeren/actions/workflows/ci.yml/badge.svg)](https://github.com/autokeren/autokeren/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/autokeren.svg)](https://pypi.org/project/autokeren/)

![autokeren TUI Screenshot](docs/assets/autogen-ui-preview.jpg)

---

## Características Principales

- **7 Modelos de IA** — kimi-code, kimi-2.6, glm-5.2, glm-flash, llama-4-scout, gemma-4 y nemotron con fallback automático.
- **PaaS Integrado** — despliega aplicaciones a Cloudflare Workers directamente desde la terminal, con enlaces (bindings) automáticos de D1 + R2 + AI.
- **Modo Multi-Agent y Auto Spawn** — ejecuta múltiples agentes en paralelo vía `/project` o permite que el agente principal llame subagentes dinámicamente usando la herramienta `spawn_agent`.
- **Soporte para Servidores MCP** — integra herramientas externas de terceros por medio de Model Context Protocol (MCP) y gestiónalas a través de `/mcp`.
- **Historial de Entrada** — navega por los comandos anteriores con las teclas de flecha `↑` / `↓` en la terminal.
- **Exportar Chat** — exporta todo el historial de chat como un archivo Markdown mediante el comando `/export`.
- **Salida en Tiempo Real (Streaming)** — renderizado de respuestas token por token en tiempo real.
- **Sistema de Permisos** — solicita confirmación antes de ejecutar comandos peligrosos de shell o escribir en archivos.
- **Memoria entre Sesiones** — almacena y carga automáticamente la memoria persistente específica del proyecto al iniciar.
- **Guardar/Reanudar Sesión (SQLite)** — guarda el estado de la conversación en una base de datos SQLite local transaccional (`sessions.db`) y reanúdala cuando quieras usando comandos slash o el flag `-r`.
- **Seguimiento de Contexto + /compact** — monitorea el uso de la ventana de contexto y resume el historial de forma automática o manual.
- **Soporte para AGENTS.md** — carga de manera automática las instrucciones específicas del proyecto para el agente de IA.
- **Renderizado Markdown** — formato enriquecido en terminal para títulos, tablas y bloques de código con resaltado de sintaxis.
- **Herramientas de KV/D1/PaaS** — lee/escribe pares de KV, realiza consultas en la base de datos D1 y gestiona proyectos directamente desde el agente.
- **Supervisor Tmux** — crea y monitorea agentes en segundo plano que sobreviven al cierre de la terminal.
- **Despliegue en CF Pages/Workers** — herramientas integradas para compilar y desplegar en Cloudflare.
- **File Explorer (F7)** — alterna el árbol de carpetas/archivos en el panel izquierdo de la TUI, haz clic en un archivo para leer su contenido automáticamente.

## Características de Vibe Coding (v0.8.0)

9 características originales que no se encuentran en otros CLIs de codificación (Claude Code, Aider, Cursor, Cline):

### Viaje en el Tiempo `/rewind`
Deshaz llamadas de herramientas y restaura el código a checkpoints anteriores. Guarda automáticamente un checkpoint después de cada escritura/modificación de archivo.
```bash
/rewind        # deshacer 1 llamada de herramienta
/rewind 3      # deshacer 3 llamadas de herramienta
/rewind list   # listar todos los checkpoints disponibles
```

### Guardián de la Arquitectura (Architecture Guardian)
Indexa el genoma del proyecto (módulos, funciones, dependencias) y bloquea funciones o módulos duplicados antes de que se escriban.
```bash
/genome         # ver el genoma del proyecto
/genome rescan  # escanear de nuevo el genoma del proyecto
/genome check   # verificar funciones duplicadas
```

### Loop Breaker
Detecta cuándo el agente está atrapado en un bucle de error/disculpa/modificación excesiva de archivos. Cambia automáticamente el modelo de IA activo.
```bash
/loop status    # ver el historial de errores del loop breaker
/loop reset     # reiniciar el rastreador de bucle
/loop break     # romper el bucle manualmente — cambiar modelo + reiniciar
```

### Auto-Revisión entre Modelos (Cross-Model Auto-Review)
Revisa diffs unstaged o staged utilizando un modelo de IA de otro proveedor para detectar puntos ciegos.
```bash
/review         # revisar los cambios no preparados (unstaged)
/review staged  # revisar los cambios preparados (staged)
```

### Guardia de Seguridad (Vibe-Security Guard)
Escanea automáticamente cada escritura de archivos en busca de filtraciones de secretos, inyección de SQL, XSS y patrones prohibidos.
```bash
/security           # escanear todo el proyecto
/security app.py    # escanear un archivo específico
```

### Ejecución de Arquitectura en Tiempo Real
Aplicación de reglas basadas en configuración en el archivo `.ak-rules.yaml` (ej: máximo de líneas por archivo, patrones prohibidos, límites de imports).

### Planificación Orientada a Specs (Spec-Driven Auto-Planning)
Entrevista guiada por IA con 20 preguntas para generar automáticamente `plan.md` y `technical-plan.md`.
```bash
/spec build a REST API     # iniciar entrevista
/spec answer mi respuesta  # responder a preguntas de la entrevista
/spec generate              # generar plan de ejecución
/spec show                  # ver plan de ejecución
/spec progress              # ver progreso del plan
```

### Agente Fantasma (Ghost Agent)
Crea agentes en segundo plano en tmux para la ejecución paralela de tareas.
```bash
/ghost fix bug in login.py  # iniciar un agente fantasma
/ghost list                 # listar todos los agentes fantasma activos
/ghost show 1               # ver salida del agente fantasma #1
/ghost kill 1               # detener el agente fantasma #1
/ghost kill all             # detener todos los agentes fantasma
```

### Herramienta de Investigación (Research Tool)
Investigación profunda en la web consultando Reddit, Hacker News y motores de búsqueda en la web.
```bash
/research python coding tools     # buscar en todas las fuentes
/research reddit asyncio tips     # buscar solo en Reddit
/research hn AI coding CLI        # buscar solo en Hacker News
/research web best practices      # buscar solo en la web general
```

## Evolución y Autocuración de AGI (v0.11.0+)

Llevando la inteligencia artificial autónoma al Autokeren CLI:

### 1. Daemon y Observador de Ciclo de Vida Continuo
Un observador de sistema asíncrono en segundo plano (SystemObserver) que monitorea logs de errores críticos y cambios de archivos para activar procesos de autocuración.

### 2. Bucle de Autoevolución / Auto-Refactorización
Refactoriza automáticamente herramientas de Python rotas, las valida con nuevas pruebas unitarias de pytest y recarga dinámicamente el registro de herramientas (hot-reload).

### 3. Memoria Semántica Local TF-IDF
Búsqueda semántica de alto rendimiento local usando Vector Space Model (VSM) con pesos TF-IDF y Cosine Similarity en una base de datos SQLite local (`memory.db`). ¡Sin necesidad de llaves de API!

### 4. Tablero Kanban TUI Interactivo (`Ctrl+K`)
Gestiona listas de tareas visualmente en la terminal, sincronizado con SQLite local. Presiona **`Ctrl+K`** para alternar el tablero en cualquier momento.

### 5. Vista de Debate Multi-Agent en Vivo (`Ctrl+D`)
Monitorea discusiones, coordinación y registros de trabajo de los Agentes Fantasma (Ghost Agents) en segundo plano en tiempo real. Presiona **`Ctrl+D`** para alternar la vista.

## Instalación y Configuración

### 1. Obtén una clave de API gratuita

Regístrate en **[developers.autokeren.com](https://developers.autokeren.com)** para obtener tu clave de API.

### 2. Instalación

#### Linux / macOS

```bash
pipx install autokeren
```

> Si no tienes pipx: `sudo apt install pipx && pipx ensurepath` (Linux) o `brew install pipx` (macOS)
> Alternativa: `pip install --user autokeren`

#### Windows (PowerShell)

**Paso 1** — Instala pipx mediante pip:

```powershell
python -m pip install --user pipx
```

**Paso 2** — Añade pipx al PATH de Windows:

```powershell
python -m pipx ensurepath
```

**Paso 3** — Reinicia PowerShell (cierra y vuelve a abrir la terminal).

**Paso 4** — Instala autokeren:

```powershell
pipx install autokeren
```

### 3. Iniciar Sesión

```bash
autokeren --login
```

Introduce tu clave de API de developers.autokeren.com.

### 4. Empieza a Programar

```bash
autokeren
```

## Guía de Inicio Rápido

### Chat TUI Interactivo (Por Defecto)

Inicia la interfaz TUI interactiva:
```bash
autokeren
```

### Prompt Único (No interactivo)

```bash
autokeren "create a hello.py file that prints hello world"
```

### Modo de Planificación (Plan Mode)

```bash
autokeren --plan
```

### Reanudar Sesión Guardada

Reanuda una sesión guardada directamente en el inicio de la terminal:
```bash
autokeren --resume nombre-sesion
# o usando el flag corto
autokeren -r nombre-sesion
```

### Elegir Modelo de IA

```bash
autokeren -m glm "refactor this function"
autokeren -m kimi "write unit tests for the tools module"
```

### Modo Google AI Studio (Gemini API)

Ejecuta autokeren directamente usando tu propia clave de API de Google AI Studio:
```bash
autokeren --aistudio
```
Si la clave de API no está configurada, se te pedirá que la introduzcas. Alternativamente, define la variable de ambiente `GEMINI_API_KEY`.

### Desplegar Aplicación

```bash
autokeren "deploy a simple shoe shop with HTML+CSS, using D1 for products"
```

El agente creará el proyecto automáticamente, escribirá el código y lo desplegará en Cloudflare Workers con enlaces a D1 y R2.

## Modelos Disponibles

| Alias | Modelo |
|---|---|
| `kimi-code` | Moonshot Kimi K2.7-Code (principal) |
| `kimi-2.6` | Moonshot Kimi K2.6 |
| `glm-5.2` | Zai GLM 5.2 (secundario) |
| `glm-flash` | Zai GLM Flash |
| `llama-4-scout` | Meta Llama 4 Scout |
| `gemma-4` | Google Gemma 4 |
| `nemotron` | NVIDIA Nemotron |

Rutas de AI Studio:

| Alias | Modelo |
|---|---|
| `gemini-3.5-flash` | Google Gemini 3.5 Flash via AI Studio (`--aistudio`) |
| `gemini-3.5-pro` | Google Gemini 3.5 Pro via AI Studio (`--aistudio`) |

Selecciona un modelo con `-m <alias>`. Por defecto: `kimi-code` con fallback a `glm-5.2`.

## Comandos y Atajos

Usa los siguientes atajos de teclado y comandos slash en el modo TUI:

### Atajos de Teclado (Hotkeys)

| Tecla | Acción | Descripción |
|---|---|---|
| **`F1`** | Ayuda | Abre el diálogo de ayuda listando comandos y atalhos |
| **`F2`** | Cambiar Modelo | Abre un modal interactivo para cambiar de modelo de IA |
| **`F3`** | Reiniciar Sesión | Restablece el historial de chat y los permisos de herramientas |
| **`F4`** | Copiar Respuesta | Copia el último mensaje de la IA al portapapeles |
| **`F5`** | Compactar | Resume/compacta el historial de la conversación |
| **`F6`** | Cambiar Idioma | Abre un modal para cambiar el idioma de la interfaz TUI |
| **`F7`** | File Explorer | Alterna la visualización del árbol de archivos en el panel izquierdo |
| **`Ctrl+K`**| Panel Kanban | Alterna el panel del tablero Kanban del proyecto |
| **`Ctrl+D`**| Debate Multi-Agent | Alterna la vista de debate de agentes en segundo plano |
| **`Ctrl+C`**| Cancelar / Parar | Detiene la generación activa de IA o herramienta de shell en ejecución |
| **`Ctrl+Q`**| Forzar Salida | Cierra inmediatamente el CLI de autokeren |

### Comandos Slash

Escribe comandos slash directamente en la caja de entrada del chat (soporta autocompletado con Tab):

| Comando | Descripción |
|---|---|
| `/help` | Muestra directrices de ayuda |
| `/q` o `/quit` | Termina la sesión del CLI |
| `/model [nombre]` | Cambia el modelo de IA (abre ventana emergente si se omite el nombre) |
| `/lang [codigo]` | Cambia el idioma de la TUI (abre ventana emergente si se omite el código, ej: `/lang id`) |
| `/export [nombre]` | Exporta la conversación actual a un archivo Markdown |
| `/copy [last\|N]` | Copia un mensaje específico al portapapeles |
| `/mcp` | Abre el administrador del servidor Model Context Protocol (MCP) |
| `/project <subcomando>`| Comando de gestión de proyecto multi-agent |
| `/compact` | Compacta el historial del chat |
| `/reset` | Restablece la sesión activa |
| `/memory` | Muestra la memoria entre sesiones guardada para el proyecto |
| `/permissions` | Muestra los permisos de herramientas concedidos actualmente |
| `/save [nombre]` | Guarda el estado de la sesión actual |
| `/resume <nombre\|id>` | Reanuda una sesión guardada |
| `/sessions` | Lista todas las sesiones guardadas |
| `/rewind [N]` | Deshaz N llamadas de herramientas y restaura el código |
| `/rewind list` | Lista todos los checkpoints disponibles |
| `/genome` | Muestra el genoma estructural del proyecto |
| `/genome rescan` | Vuelve a escanear el genoma de arquitectura del proyecto |
| `/genome check` | Verifica si existen funciones duplicadas |
| `/loop status` | Muestra el historial de errores del loop breaker |
| `/loop reset` | Reinicia las estadísticas del loop breaker |
| `/loop break` | Rompe el bucle manualmente (cambia el modelo activo) |
| `/review [staged]` | Ejecuta revisión de código cruzada entre modelos |
| `/security [file]` | Realiza auditoría de seguridad en un archivo |
| `/spec <requisito>` | Inicia la entrevista de recopilación de requisitos |
| `/spec answer <texto>` | Envía respuesta para la pregunta de la entrevista |
| `/spec generate` | Genera los archivos plan.md y technical-plan.md |
| `/spec show` | Muestra el plan de ejecución |
| `/spec progress` | Acompaña el progreso de la ejecución |
| `/ghost <tarea>` | Inicia un agente fantasma en segundo plano |
| `/ghost list` | Lista todos los agentes fantasma activos en segundo plano |
| `/ghost show <id>` | Muestra logs de un agente fantasma específico |
| `/ghost kill <id\|all>` | Detiene los agentes fantasma en ejecución |
| `/research <query>` | Busca en Reddit, Hacker News y motores de búsqueda en la web |
| `/deploy <desc>` | Crea el proyecto y lo despliega directamente en Cloudflare Pages/Workers |

## Configuraciones Guardadas

El archivo de configuración se encuentra en `~/.config/autokeren/config.yaml`.

```yaml
auth:
  mode: "platform"       # "platform" (por defecto), "direct" o "aistudio"
  api_key: ""            # Clave de API de developers.autokeren.com
  gemini_api_key: ""     # Clave de API de Google AI Studio (solo para el modo "aistudio")

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
  # Características de Vibe coding
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

### Variables de Entorno

| Variable | Descripción |
|---|---|
| `AUTOKEREN_API_KEY` | Reemplaza la clave de API de la configuración |
| `GEMINI_API_KEY` | Clave de API de Google AI Studio |
| `AUTOKEREN_CONFIG_DIR` | Directorio de configuración personalizado (por defecto `~/.config/autokeren`) |

## Actualización

Para actualizar a la versión más reciente:
```bash
pipx upgrade autokeren
```

## Arquitectura Híbrida Go + Python

`autokeren` utiliza una arquitectura híbrida de alto rendimiento que combina un driver Go para la interfaz con un núcleo en Python para la inteligencia artificial:

1.  **Frontend y TUI (Go):**
    Construido utilizando los frameworks **Bubble Tea** y **Lip Gloss**. Gestiona el layout, el árbol de archivos, el historial de comandos, Kanban, el debate de agentes y controla los procesos del navegador Go-Rod.
2.  **AI Core y Brain (Python):**
    Gestiona el ciclo agentic multi-turn, enrutamiento de fallback multi-model, análisis estático (AST parsing) y escaneo de seguridad.
3.  **IPC (Inter-Process Communication):**
    Conexión asíncrona **JSON-RPC 2.0** establecida a través de un **Socket TCP Local** en un puerto dinámico.
    
    *¿Por qué un Socket TCP Local?*
    Esto separa los paquetes de datos de JSON-RPC del flujo de salida estándar (stdout) del proceso Python. Cualquier log accidental (`print()`) o warning de dependencias se redirige al stderr del background, evitando crashes del analizador y congelaciones de la TUI (*TUI freeze*).

## Contribución

¡Las contribuciones son bienvenidas! Haz un fork del repositorio, crea una rama (branch) para tu función y envía tu PR.

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Antes de enviar código, asegúrate de que las pruebas `ruff check .`, `mypy autokeren` y `pytest` pasen con éxito.

## Licencia

Este proyecto está licenciado bajo la licencia MIT - consulta el archivo [LICENSE](LICENSE) para obtener detalles.

## Descargo de Responsabilidad

autokeren es un proyecto independiente y **no está afiliado, respaldado ni patrocinado por Cloudflare, Inc.** "Cloudflare" y los nombres de productos asociados son marcas comerciales registradas de Cloudflare, Inc. autokeren utiliza las APIs públicas de Cloudflare y la infraestructura de Workers como un cliente de terceros.
