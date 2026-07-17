package ipc

import (
	"bufio"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/atotto/clipboard"
	"github.com/autokeren/autokeren/internal/config"
	contextstore "github.com/autokeren/autokeren/internal/context"
	"github.com/autokeren/autokeren/internal/engine"
	"github.com/autokeren/autokeren/internal/model"
	sessionstore "github.com/autokeren/autokeren/internal/session"
	"github.com/autokeren/autokeren/internal/tool"
)

// JSONRPCMessage mewakili request, response, atau notification JSON-RPC 2.0
type JSONRPCMessage struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method,omitempty"`
	Params  json.RawMessage `json:"params,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *JSONRPCError   `json:"error,omitempty"`
	ID      interface{}     `json:"id,omitempty"`
}

type JSONRPCError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// IPCCallbacks mewakili callback dari daemon untuk merespon turn atau event
type IPCCallbacks struct {
	OnModelStart      func()
	OnModelEnd        func(content string, modelID string, sessionID string, sessionName string, usage map[string]interface{})
	OnChunk           func(text string)
	OnToolStart       func(name string, arguments map[string]interface{})
	OnToolEnd         func(name string, result map[string]interface{})
	OnToolOutput      func(name string, line string)
	OnRetry           func(attempt int, delay float64, message string)
	OnSessionSaved    func(sessionID string, sessionName string)
	ConfirmPermission func(name string, desc string, args map[string]interface{}) bool
	OnError           func(message string)
}

type Client struct {
	cmd       *exec.Cmd
	conn      net.Conn
	callbacks *IPCCallbacks

	pending     map[int64]chan *JSONRPCMessage
	pendingLock sync.Mutex
	nextID      int64

	isClosed              int32
	local                 bool
	localRoot             string
	localConfig           config.Config
	localConfigPath       string
	localSession          string
	localSessionName      string
	localSessions         *sessionstore.Manager
	localNeuronsUsed      int
	localNeuronsRemaining int
	localNeuronsQuota     int
	localRunMu            sync.Mutex
	localRunCancel        context.CancelFunc
	localDebug            bool
}

func NewClient(callbacks *IPCCallbacks) *Client {
	return &Client{
		callbacks: callbacks,
		pending:   make(map[int64]chan *JSONRPCMessage),
		nextID:    1,
	}
}

func (c *Client) Start(projectRoot string, configPath string, opts map[string]interface{}) error {
	if opts != nil && opts["engine"] == "go" {
		return c.startLocal(projectRoot, configPath)
	}
	if c.cmd != nil {
		return errors.New("client sudah berjalan")
	}

	// 1. Buat TCP Listener pada localhost port random
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return fmt.Errorf("gagal membuat TCP listener: %v", err)
	}
	defer listener.Close()

	addr := listener.Addr().(*net.TCPAddr)
	port := addr.Port

	// Dapatkan path interpreter Python dari parent process
	pythonPath := os.Getenv("AUTOKEREN_PYTHON_PATH")
	if pythonPath == "" {
		// Cek apakah ada virtual environment lokal (.venv)
		localVenv := filepath.Join(projectRoot, ".venv", "bin", "python3")
		if _, err := os.Stat(localVenv); err == nil {
			pythonPath = localVenv
		} else {
			localVenvWin := filepath.Join(projectRoot, ".venv", "Scripts", "python.exe")
			if _, err := os.Stat(localVenvWin); err == nil {
				pythonPath = localVenvWin
			}
		}
	}

	if pythonPath == "" {
		// Fallback ke pencarian PATH biasa jika dijalankan terpisah
		var err error
		pythonPath, err = exec.LookPath("python3")
		if err != nil {
			pythonPath, err = exec.LookPath("python")
			if err != nil {
				return errors.New("interpreter python3 tidak ditemukan di PATH")
			}
		}
	}

	// 2. Jalankan subprocess Python daemon dengan melewatkan argumen port
	c.cmd = exec.Command(pythonPath, "-m", "autokeren.daemon", "--port", strconv.Itoa(port))
	c.cmd.Env = append(os.Environ(), "PYTHONPATH=.", "PYTHONUNBUFFERED=1")

	// Alihkan stdout & stderr daemon ke os.Stderr
	// Ini memisahkan stdout/print() Python biasa agar tidak mencemari JSON-RPC
	c.cmd.Stdout = os.Stderr
	c.cmd.Stderr = os.Stderr

	if err := c.cmd.Start(); err != nil {
		return fmt.Errorf("gagal menjalankan daemon: %v", err)
	}

	// 3. Terima koneksi incoming dari Python daemon
	// Set deadline agar tidak gantung selamanya jika daemon gagal meluncur
	if tcpListener, ok := listener.(*net.TCPListener); ok {
		tcpListener.SetDeadline(time.Now().Add(10 * time.Second))
	}
	conn, err := listener.Accept()
	if err != nil {
		c.cmd.Process.Kill()
		return fmt.Errorf("gagal menerima koneksi dari daemon: %v", err)
	}
	c.conn = conn

	// Mulai mendengarkan data di goroutine background
	go c.listen()

	// Kirim inisialisasi awal
	initParams := map[string]interface{}{
		"project_root": projectRoot,
	}
	if configPath != "" {
		initParams["config_path"] = configPath
	}
	for k, v := range opts {
		initParams[k] = v
	}

	var respStr string
	err = c.Call("agent.init", initParams, &respStr)
	if err != nil {
		c.Close()
		return fmt.Errorf("gagal inisialisasi agen: %v", err)
	}

	return nil
}

func (c *Client) Close() {
	if c.local {
		c.local = false
		atomic.StoreInt32(&c.isClosed, 1)
		return
	}
	if atomic.CompareAndSwapInt32(&c.isClosed, 0, 1) {
		if c.conn != nil {
			c.conn.Close()
		}
		if c.cmd != nil && c.cmd.Process != nil {
			c.cmd.Process.Kill()
		}
		GetBrowserManager().Close()
	}
}

func (c *Client) startLocal(projectRoot, configPath string) error {
	cfg, err := config.Load(configPath)
	if err != nil {
		return err
	}
	c.local = true
	c.localRoot = projectRoot
	c.localConfig = cfg
	c.localConfigPath = configPath
	c.localSession = "default"
	c.localSessionName = "default"
	c.localSessions, err = sessionstore.NewManager(projectRoot)
	if err != nil {
		return err
	}
	atomic.StoreInt32(&c.isClosed, 0)
	return nil
}

func (c *Client) callLocal(method string, params interface{}, reply interface{}) error {
	switch method {
	case "agent.run":
		input, _ := params.(map[string]interface{})["user_input"].(string)
		if input == "" {
			return errors.New("user_input kosong")
		}
		if handled, err := c.localSlash(input, reply); handled {
			return err
		}
		events := engine.Events{
			OnChunk: func(text string) {
				if c.callbacks != nil && c.callbacks.OnChunk != nil {
					c.callbacks.OnChunk(text)
				}
			},
			OnToolStart: func(name string, args map[string]any) {
				if c.callbacks != nil && c.callbacks.OnToolStart != nil {
					c.callbacks.OnToolStart(name, args)
				}
			},
			OnToolOutput: func(name, line string) {
				if c.callbacks != nil && c.callbacks.OnToolOutput != nil {
					c.callbacks.OnToolOutput(name, line)
				}
			},
			OnToolEnd: func(name string, result tool.Result) {
				if c.callbacks != nil && c.callbacks.OnToolEnd != nil {
					raw, _ := json.Marshal(result)
					var value map[string]interface{}
					_ = json.Unmarshal(raw, &value)
					c.callbacks.OnToolEnd(name, value)
				}
			},
			ConfirmPermission: func(name, desc string, args map[string]any) bool {
				if c.callbacks != nil && c.callbacks.ConfirmPermission != nil {
					return c.callbacks.ConfirmPermission(name, desc, args)
				}
				return name != "run_shell"
			},
			OnResponse: func(response model.Response) {
				c.localNeuronsUsed = response.Usage.NeuronsUsed
				c.localNeuronsRemaining = response.Usage.NeuronsRemaining
				c.localNeuronsQuota = response.Usage.NeuronsQuota
			},
			OnSessionSaved: func(id, name string) {
				c.localSession = id
				c.localSessionName = name
				if c.callbacks != nil && c.callbacks.OnSessionSaved != nil {
					c.callbacks.OnSessionSaved(id, name)
				}
			},
		}
		runCtx, cancel := context.WithCancel(context.Background())
		c.localRunMu.Lock()
		c.localRunCancel = cancel
		c.localRunMu.Unlock()
		content, err := engine.RunStandaloneEvents(runCtx, c.localConfig, c.localRoot, input, events, c.localSession)
		c.localRunMu.Lock()
		c.localRunCancel = nil
		c.localRunMu.Unlock()
		cancel()
		if err != nil {
			if c.callbacks != nil && c.callbacks.OnError != nil {
				c.callbacks.OnError(err.Error())
			}
			return err
		}
		if c.callbacks != nil && c.callbacks.OnModelEnd != nil {
			c.callbacks.OnModelEnd(content, c.localConfig.Cloudflare.PrimaryModel, c.localSession, c.localSessionName, nil)
		}
		if reply != nil {
			raw, _ := json.Marshal(map[string]any{"content": content, "session_id": c.localSession, "session_name": c.localSessionName})
			return json.Unmarshal(raw, reply)
		}
		return nil
	case "agent.status":
		status := map[string]any{"running": false, "engine": "go", "model_id": c.localConfig.Cloudflare.PrimaryModel, "model_name": c.localConfig.Cloudflare.PrimaryModel, "session_id": c.localSession, "session_name": c.localSessionName, "context_info": c.localContextInfo()}
		if c.localNeuronsQuota > 0 {
			status["status_bar_info"] = map[string]any{"neurons_used": c.localNeuronsUsed, "neurons_remaining": c.localNeuronsRemaining, "neurons_quota": c.localNeuronsQuota}
		}
		if data, err := os.ReadFile(filepath.Join(c.localRoot, ".autokeren", "kanban.json")); err == nil {
			var tasks any
			if json.Unmarshal(data, &tasks) == nil {
				status["kanban_tasks"] = tasks
			}
		}
		if data, err := os.ReadFile(filepath.Join(c.localRoot, ".autokeren", "todos.json")); err == nil {
			var todos any
			if json.Unmarshal(data, &todos) == nil {
				status["todos"] = todos
			}
		}
		if reply != nil {
			raw, _ := json.Marshal(status)
			return json.Unmarshal(raw, reply)
		}
		return nil
	case "agent.reset":
		c.localSession = "default"
		c.localSessionName = "default"
		return nil
	case "agent.compact":
		if c.localSession == "default" {
			if reply != nil {
				return json.Unmarshal([]byte(`{"message":"Context sudah cukup singkat, tidak perlu compact."}`), reply)
			}
			return nil
		}
		sessions, err := c.localSessionManager()
		if err != nil {
			return err
		}
		data, err := sessions.Load(c.localSession)
		if err != nil {
			return err
		}
		store := contextstore.New(c.localConfig.Autokeren.ContextWindow, false, c.localConfig.Autokeren.AutoCompactThreshold)
		store.SetCompactTail(c.localConfig.Autokeren.CompactTailTurns)
		store.Replace(data.Messages)
		before, after, changed := store.Compact()
		message := "Context sudah cukup singkat, tidak perlu compact."
		if changed {
			data.Messages = store.Messages()
			saved, saveErr := sessions.Save(c.localSessionName, data.Messages, data.Usage, c.localSession)
			if saveErr != nil {
				return saveErr
			}
			c.localSession = saved.ID
			message = fmt.Sprintf("Context di-compact: pesan lama diringkas. Token %d → %d (hemat %d).", before, after, before-after)
		}
		if reply != nil {
			raw, _ := json.Marshal(map[string]any{"message": message})
			return json.Unmarshal(raw, reply)
		}
		return nil
	case "agent.interrupt":
		c.localRunMu.Lock()
		cancel := c.localRunCancel
		c.localRunMu.Unlock()
		if cancel != nil {
			cancel()
		}
		return nil
	case "agent.save_session":
		args, _ := params.(map[string]interface{})
		name, _ := args["name"].(string)
		if name == "" {
			name = fmt.Sprintf("session-%d", time.Now().Unix())
		}
		sessions, err := c.localSessionManager()
		if err != nil {
			return err
		}
		data, loadErr := sessions.Load(c.localSession)
		if loadErr != nil && !errors.Is(loadErr, sql.ErrNoRows) {
			return loadErr
		}
		saved, err := sessions.Save(name, data.Messages, data.Usage, "")
		if err != nil {
			return err
		}
		c.localSession = saved.ID
		c.localSessionName = name
		if reply != nil {
			return json.Unmarshal([]byte(fmt.Sprintf(`{"message":"Session '%s' disimpan.","session_id":%q,"session_name":%q,"name":%q}`, name, saved.ID, name, name)), reply)
		}
		return nil
	case "agent.resume_session":
		args, _ := params.(map[string]interface{})
		identifier, _ := args["identifier"].(string)
		if identifier == "" {
			return errors.New("session identifier kosong")
		}
		sessions, err := c.localSessionManager()
		if err != nil {
			return err
		}
		data, err := sessions.Load(identifier)
		if err != nil {
			return fmt.Errorf("session %q tidak ditemukan", identifier)
		}
		c.localSession = data.ID
		c.localSessionName = data.Name
		if reply != nil {
			raw, _ := json.Marshal(map[string]any{"message": "Session " + c.localSessionName + " berhasil di-resume.", "session_id": c.localSession, "session_name": c.localSessionName, "messages": data.Messages})
			return json.Unmarshal(raw, reply)
		}
		return nil
	case "agent.list_sessions":
		sessions, err := c.localSessionManager()
		if err != nil {
			return err
		}
		entries, err := sessions.List()
		if err != nil {
			return err
		}
		items := make([]map[string]interface{}, 0)
		for _, entry := range entries {
			items = append(items, map[string]interface{}{"id": entry.ID, "name": entry.Name, "created_at": entry.Timestamp, "message_count": entry.Messages})
		}
		if reply != nil {
			raw, _ := json.Marshal(map[string]interface{}{"sessions": items})
			return json.Unmarshal(raw, reply)
		}
		return nil
	case "agent.list_models":
		models := c.localModels()
		if reply != nil {
			raw, _ := json.Marshal(models)
			return json.Unmarshal(raw, reply)
		}
		return nil
	case "agent.switch_model":
		args, _ := params.(map[string]interface{})
		if modelID, ok := args["model_id"].(string); ok && modelID != "" {
			c.localConfig.Cloudflare.PrimaryModel = modelID
			if c.localConfigPath != "" {
				_ = config.Save(c.localConfigPath, c.localConfig)
			}
		}
		return nil
	case "kanban.add", "kanban.move", "kanban.delete":
		args, _ := params.(map[string]interface{})
		toolArgs := make(map[string]any, len(args)+1)
		for key, value := range args {
			toolArgs[key] = value
		}
		action := strings.TrimPrefix(method, "kanban.")
		toolArgs["action"] = action
		result := tool.NewKanban(c.localRoot).Run(context.Background(), toolArgs, nil)
		if !result.OK {
			return errors.New(result.Error)
		}
		if reply != nil {
			raw, _ := json.Marshal(map[string]interface{}{"ok": true, "tasks": result.Output})
			return json.Unmarshal(raw, reply)
		}
		return nil
	default:
		return fmt.Errorf("method %s belum tersedia di Go TUI adapter", method)
	}
}

func (c *Client) localModels() []map[string]interface{} {
	current := c.localConfig.Cloudflare.PrimaryModel
	endpoint := strings.TrimRight(c.localConfig.Auth.BaseURL, "/") + "/v1/models"
	request, err := http.NewRequest(http.MethodGet, endpoint, nil)
	if err == nil {
		if c.localConfig.Auth.APIKey != "" {
			request.Header.Set("Authorization", "Bearer "+c.localConfig.Auth.APIKey)
		}
		if response, requestErr := (&http.Client{Timeout: 10 * time.Second}).Do(request); requestErr == nil {
			defer response.Body.Close()
			if response.StatusCode >= 200 && response.StatusCode < 300 {
				data, _ := io.ReadAll(io.LimitReader(response.Body, 2<<20))
				var envelope struct {
					Data []map[string]interface{} `json:"data"`
				}
				if json.Unmarshal(data, &envelope) == nil && len(envelope.Data) > 0 {
					for _, model := range envelope.Data {
						if _, ok := model["name"]; !ok {
							model["name"] = model["id"]
						}
						model["active"] = fmt.Sprint(model["id"]) == current
					}
					return envelope.Data
				}
			}
		}
	}
	ids := []string{"@cf/moonshotai/kimi-k2.7-code", "@cf/moonshotai/kimi-k2.6", "@cf/zai-org/glm-5.2", "@cf/zai-org/glm-4.7-flash", "@cf/meta/llama-4-scout-17b-16e-instruct", "@cf/google/gemma-4-26b-a4b-it", "kimi-code", "kimi-2.6", "glm-5.2", "gpt-5.6", "gpt-4o", "gemini-2.5-pro", "gemini-2.5-flash"}
	models := make([]map[string]interface{}, 0, len(ids)+1)
	seen := map[string]bool{}
	for _, id := range append([]string{current}, ids...) {
		if id == "" || seen[id] {
			continue
		}
		seen[id] = true
		models = append(models, map[string]interface{}{"id": id, "name": id, "active": id == current})
	}
	return models
}

func (c *Client) localSessionManager() (*sessionstore.Manager, error) {
	if c.localSessions != nil {
		return c.localSessions, nil
	}
	manager, err := sessionstore.NewManager(c.localRoot)
	if err != nil {
		return nil, err
	}
	c.localSessions = manager
	return manager, nil
}

func (c *Client) copySessionMessage(selector string) (string, error) {
	if c.localSession == "default" {
		return "", errors.New("belum ada pesan untuk disalin")
	}
	sessions, err := c.localSessionManager()
	if err != nil {
		return "", err
	}
	data, err := sessions.Load(c.localSession)
	if err != nil {
		return "", err
	}
	content, err := copyableSessionMessage(data.Messages, selector)
	if err != nil {
		return "", err
	}
	if err := clipboard.WriteAll(content); err == nil {
		return "Pesan disalin ke clipboard.", nil
	}
	file, err := os.CreateTemp("", "autokeren-copy-*.txt")
	if err != nil {
		return "", err
	}
	path := file.Name()
	if _, err := file.WriteString(content); err != nil {
		_ = file.Close()
		return "", err
	}
	if err := file.Close(); err != nil {
		return "", err
	}
	return "Clipboard tidak tersedia. Pesan tersimpan: " + path, nil
}

func copyableSessionMessage(messages []model.Message, selector string) (string, error) {
	visible := make([]model.Message, 0, len(messages))
	for _, message := range messages {
		if (message.Role == "user" || message.Role == "assistant") && message.Content != "" {
			visible = append(visible, message)
		}
	}
	if len(visible) == 0 {
		return "", errors.New("belum ada pesan untuk disalin")
	}
	if selector == "" || selector == "last" {
		return visible[len(visible)-1].Content, nil
	}
	index, err := strconv.Atoi(selector)
	if err != nil || index < 1 || index > len(visible) {
		return "", fmt.Errorf("pesan dengan indeks %q tidak ditemukan", selector)
	}
	return visible[index-1].Content, nil
}

func (c *Client) localContextInfo() map[string]any {
	tokens := 0
	if sessions, err := c.localSessionManager(); err == nil && c.localSession != "default" {
		data, loadErr := sessions.Load(c.localSession)
		if loadErr == nil {
			for _, message := range data.Messages {
				tokens += len([]rune(message.Role+" "+message.Content+" "+message.Name))/4 + len(message.ToolCalls)*8
			}
		}
	}
	window := c.localConfig.Autokeren.ContextWindow
	if window <= 0 {
		window = 262144
	}
	return map[string]any{"tokens": tokens, "window": window, "pct": float64(tokens) / float64(window) * 100}
}

func (c *Client) localSlash(input string, reply interface{}) (bool, error) {
	parts := strings.Fields(input)
	if len(parts) == 0 || !strings.HasPrefix(parts[0], "/") {
		return false, nil
	}
	var output string
	switch parts[0] {
	case "/help":
		output = "Perintah: /help, /model, /lang, /permissions, /memory, /export, /mcp, /save, /resume, /sessions, /ghost, /research, /proof, /review, /security, /rewind, /config, /local, /approval, /reset, /q"
	case "/permissions":
		output = "Tool berisiko akan meminta izin di TUI. Gunakan /approval all untuk mengizinkan semua tool selama sesi ini, atau /approval ask untuk kembali bertanya."
	case "/debug":
		c.localDebug = !c.localDebug
		if c.localDebug {
			_ = os.Setenv("AUTOKEREN_DEBUG", "1")
			output = "Mode Debug AKTIF. Detail error akan ditampilkan lebih lengkap."
		} else {
			_ = os.Unsetenv("AUTOKEREN_DEBUG")
			output = "Mode Debug NON-AKTIF."
		}
	case "/copy":
		selector := "last"
		if len(parts) > 1 {
			selector = parts[1]
		}
		message, err := c.copySessionMessage(selector)
		if err != nil {
			return true, err
		}
		output = message
	case "/status":
		output = fmt.Sprintf("engine: go\nmodel: %s\nproject: %s", c.localConfig.Cloudflare.PrimaryModel, c.localRoot)
	case "/lang":
		if len(parts) == 1 {
			output = fmt.Sprintf("Bahasa aktif: %s. Gunakan /lang <kode>.", c.localConfig.Autokeren.Language)
			break
		}
		language := strings.ToLower(parts[1])
		if len(language) < 2 || len(language) > 8 {
			return true, errors.New("kode bahasa tidak valid")
		}
		c.localConfig.Autokeren.Language = language
		if err := config.Save(c.localConfigPath, c.localConfig); err != nil {
			return true, err
		}
		output = "Bahasa aktif diubah ke: " + language
	case "/config":
		raw, _ := json.MarshalIndent(c.localConfig, "", "  ")
		output = string(raw)
	case "/memory":
		data, err := os.ReadFile(filepath.Join(c.localRoot, ".autokeren", "memory.md"))
		if err != nil && !os.IsNotExist(err) {
			return true, err
		}
		output = string(data)
		if output == "" {
			output = "Memory project kosong."
		}
	case "/export":
		name := "autokeren_export_" + time.Now().Format("20060102_150405") + ".md"
		if len(parts) > 1 {
			name = parts[1]
			if !strings.HasSuffix(name, ".md") {
				name += ".md"
			}
		}
		if c.localSession == "default" {
			output = "Belum ada percakapan untuk diekspor."
			break
		}
		sessions, err := c.localSessionManager()
		if err != nil {
			return true, err
		}
		data, err := sessions.Load(c.localSession)
		if errors.Is(err, sql.ErrNoRows) {
			output = "Belum ada percakapan untuk diekspor."
			break
		}
		if err != nil {
			return true, err
		}
		var builder strings.Builder
		builder.WriteString("# autokeren Chat Export\n\n")
		for _, message := range data.Messages {
			if message.Role != "user" && message.Role != "assistant" {
				continue
			}
			role := "Assistant"
			if message.Role == "user" {
				role = "User"
			}
			builder.WriteString("## " + role + "\n\n" + message.Content + "\n\n---\n\n")
		}
		if builder.Len() == len("# autokeren Chat Export\n\n") {
			output = "Belum ada percakapan untuk diekspor."
			break
		}
		if err := os.WriteFile(filepath.Join(c.localRoot, name), []byte(builder.String()), 0o600); err != nil {
			return true, err
		}
		output = "Export tersimpan: " + filepath.Join(c.localRoot, name)
	case "/local":
		if len(parts) == 1 {
			output = "Local endpoint: " + c.localConfig.Auth.LocalEndpoint
			break
		}
		c.localConfig.Auth.LocalEndpoint = parts[1]
		if err := config.Save(c.localConfigPath, c.localConfig); err != nil {
			return true, err
		}
		output = "Local endpoint diubah: " + c.localConfig.Auth.LocalEndpoint
	case "/mcp":
		if len(parts) > 1 && parts[1] == "add" {
			if len(parts) < 4 {
				return true, errors.New("format: /mcp add <name> <command>")
			}
			server := config.MCPServer{Name: parts[2], Command: parts[3:], Enabled: true}
			c.localConfig.MCPServers = append(c.localConfig.MCPServers, server)
			if err := config.Save(c.localConfigPath, c.localConfig); err != nil {
				return true, err
			}
			output = fmt.Sprintf("MCP server %s tersimpan.", server.Name)
		} else if len(c.localConfig.MCPServers) == 0 {
			output = "Belum ada MCP server."
		} else {
			for _, server := range c.localConfig.MCPServers {
				output += fmt.Sprintf("- %s: %s\n", server.Name, strings.Join(server.Command, " "))
			}
		}
	case "/rewind":
		steps := 1
		if len(parts) > 1 {
			if n, err := strconv.Atoi(parts[1]); err == nil && n > 0 {
				steps = n
			}
		}
		result := (tool.Rewind{Root: c.localRoot}).Run(context.Background(), map[string]any{"steps": float64(steps)}, nil)
		output = fmt.Sprint(result.Output)
		if !result.OK {
			output = result.Error
		}
	case "/review":
		result := (tool.Review{Root: c.localRoot}).Run(context.Background(), map[string]any{}, nil)
		output = fmt.Sprint(result.Output)
		if !result.OK {
			output = result.Error
		}
	case "/security":
		result := (tool.SecurityScan{Root: c.localRoot}).Run(context.Background(), map[string]any{}, nil)
		output = fmt.Sprint(result.Output)
		if !result.OK {
			output = result.Error
		}
	case "/proof":
		action := "list"
		if len(parts) > 1 {
			action = parts[1]
		}
		args := map[string]any{"action": action}
		if action == "replay" && len(parts) > 2 {
			args["proof_id"] = parts[2]
		} else if len(parts) > 2 {
			args["proof_id"] = parts[2]
		}
		if action == "plan" {
			if len(parts) < 4 {
				return true, errors.New("format: /proof plan <title> <criterion1>|<criterion2>")
			}
			args["title"] = parts[2]
			criteria := strings.Split(strings.Join(parts[3:], " "), "|")
			items := make([]any, 0, len(criteria))
			for _, criterion := range criteria {
				if value := strings.TrimSpace(criterion); value != "" {
					items = append(items, value)
				}
			}
			args["criteria"] = items
		}
		result := (tool.Proof{Root: c.localRoot}).Run(context.Background(), args, nil)
		output = fmt.Sprint(result.Output)
		if !result.OK {
			output = result.Error
		}
	case "/research":
		if len(parts) < 2 {
			return true, errors.New("format: /research <query>")
		}
		result := (tool.Research{}).Run(context.Background(), map[string]any{"query": strings.Join(parts[1:], " ")}, nil)
		output = fmt.Sprint(result.Output)
		if !result.OK {
			output = result.Error
		}
	default:
		return false, nil
	}
	if c.callbacks != nil && c.callbacks.OnChunk != nil {
		c.callbacks.OnChunk(output)
	}
	if c.callbacks != nil && c.callbacks.OnModelEnd != nil {
		c.callbacks.OnModelEnd(output, c.localConfig.Cloudflare.PrimaryModel, c.localSession, c.localSessionName, nil)
	}
	if reply != nil {
		raw, _ := json.Marshal(map[string]any{"content": output, "ok": true})
		_ = json.Unmarshal(raw, reply)
	}
	return true, nil
}

func (c *Client) send(msg *JSONRPCMessage) error {
	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	data = append(data, '\n')

	c.pendingLock.Lock()
	defer c.pendingLock.Unlock()

	if atomic.LoadInt32(&c.isClosed) == 1 {
		return errors.New("ipc client closed")
	}

	_, err = c.conn.Write(data)
	return err
}

func (c *Client) Call(method string, params interface{}, reply interface{}) error {
	if c.local {
		return c.callLocal(method, params, reply)
	}
	id := atomic.AddInt64(&c.nextID, 1)

	rawParams, err := json.Marshal(params)
	if err != nil {
		return err
	}

	ch := make(chan *JSONRPCMessage, 1)
	c.pendingLock.Lock()
	c.pending[id] = ch
	c.pendingLock.Unlock()

	defer func() {
		c.pendingLock.Lock()
		delete(c.pending, id)
		c.pendingLock.Unlock()
	}()

	msg := &JSONRPCMessage{
		JSONRPC: "2.0",
		Method:  method,
		Params:  rawParams,
		ID:      id,
	}

	if err := c.send(msg); err != nil {
		return err
	}

	// Tunggu response
	resp := <-ch
	if resp == nil {
		return errors.New("daemon process exited or disconnected")
	}

	if resp.Error != nil {
		return fmt.Errorf("daemon error (%d): %s", resp.Error.Code, resp.Error.Message)
	}

	if reply != nil && len(resp.Result) > 0 {
		return json.Unmarshal(resp.Result, reply)
	}

	return nil
}

func (c *Client) handleNotification(msg *JSONRPCMessage) {
	if c.callbacks == nil {
		return
	}

	switch msg.Method {
	case "ui.on_model_start":
		if c.callbacks.OnModelStart != nil {
			c.callbacks.OnModelStart()
		}
	case "ui.on_model_end":
		if c.callbacks.OnModelEnd != nil {
			var p struct {
				Content     string                 `json:"content"`
				ModelID     string                 `json:"model_id"`
				SessionID   string                 `json:"session_id"`
				SessionName string                 `json:"session_name"`
				Usage       map[string]interface{} `json:"usage"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnModelEnd(p.Content, p.ModelID, p.SessionID, p.SessionName, p.Usage)
			}
		}
	case "ui.on_chunk":
		if c.callbacks.OnChunk != nil {
			var p struct {
				Text string `json:"text"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnChunk(p.Text)
			}
		}
	case "ui.on_tool_start":
		if c.callbacks.OnToolStart != nil {
			var p struct {
				Name      string                 `json:"name"`
				Arguments map[string]interface{} `json:"arguments"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnToolStart(p.Name, p.Arguments)
			}
		}
	case "ui.on_tool_end":
		if c.callbacks.OnToolEnd != nil {
			var p struct {
				Name   string                 `json:"name"`
				Result map[string]interface{} `json:"result"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnToolEnd(p.Name, p.Result)
			}
		}
	case "ui.on_tool_output":
		if c.callbacks.OnToolOutput != nil {
			var p struct {
				Name string `json:"name"`
				Line string `json:"line"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnToolOutput(p.Name, p.Line)
			}
		}
	case "ui.on_retry":
		if c.callbacks.OnRetry != nil {
			var p struct {
				Attempt int     `json:"attempt"`
				Delay   float64 `json:"delay"`
				Message string  `json:"message"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnRetry(p.Attempt, p.Delay, p.Message)
			}
		}
	case "ui.session_saved":
		if c.callbacks.OnSessionSaved != nil {
			var p struct {
				SessionID   string `json:"session_id"`
				SessionName string `json:"session_name"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnSessionSaved(p.SessionID, p.SessionName)
			}
		}
	case "ui.error":
		if c.callbacks.OnError != nil {
			var p struct {
				Message string `json:"message"`
			}
			if err := json.Unmarshal(msg.Params, &p); err == nil {
				c.callbacks.OnError(p.Message)
			}
		}
	}
}

func (c *Client) handleRequest(msg *JSONRPCMessage) {
	// Peta method request masuk dari Python (seperti ui.confirm_permission)
	if msg.Method == "ui.confirm_permission" {
		var p struct {
			ToolName    string                 `json:"tool_name"`
			Description string                 `json:"description"`
			Arguments   map[string]interface{} `json:"arguments"`
		}

		allowed := false
		if err := json.Unmarshal(msg.Params, &p); err == nil && c.callbacks != nil && c.callbacks.ConfirmPermission != nil {
			allowed = c.callbacks.ConfirmPermission(p.ToolName, p.Description, p.Arguments)
		}

		// Kirim balik hasil konfirmasi sebagai response
		resBytes, _ := json.Marshal(allowed)
		resp := &JSONRPCMessage{
			JSONRPC: "2.0",
			Result:  resBytes,
			ID:      msg.ID,
		}
		c.send(resp)
	} else if msg.Method == "ui.control_browser" {
		var p struct {
			Action string                 `json:"action"`
			Args   map[string]interface{} `json:"args"`
		}

		var result interface{}
		var err error
		if err = json.Unmarshal(msg.Params, &p); err == nil {
			bm := GetBrowserManager()
			result, err = bm.Execute(p.Action, p.Args)
		}

		respMap := map[string]interface{}{
			"ok":     err == nil,
			"output": result,
		}
		if err != nil {
			respMap["error"] = err.Error()
		}

		resBytes, _ := json.Marshal(respMap)
		resp := &JSONRPCMessage{
			JSONRPC: "2.0",
			Result:  resBytes,
			ID:      msg.ID,
		}
		c.send(resp)
	}
}

func (c *Client) listen() {
	scanner := bufio.NewScanner(c.conn)
	// Set buffer limit to 64MB to handle large payloads (like screenshots or file diffs)
	const maxCapacity = 64 * 1024 * 1024
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, maxCapacity)

	for scanner.Scan() {
		data := scanner.Bytes()
		if len(data) == 0 {
			continue
		}

		var msg JSONRPCMessage
		if err := json.Unmarshal(data, &msg); err != nil {
			if c.callbacks != nil && c.callbacks.OnError != nil {
				c.callbacks.OnError(fmt.Sprintf("gagal parse pesan daemon: %v | raw: %s", err, string(data)))
			}
			continue
		}

		// Kasus 1: Notifikasi (method terisi, id kosong)
		if msg.Method != "" && msg.ID == nil {
			c.handleNotification(&msg)
			continue
		}

		// Kasus 2: Request masuk (method terisi, id terisi)
		if msg.Method != "" && msg.ID != nil {
			c.handleRequest(&msg)
			continue
		}

		// Kasus 3: Response atas request (id terisi, method kosong)
		if msg.ID != nil {
			var numericID int64
			// Nilai ID dari json unmarshal bisa bertipe float64
			if f, ok := msg.ID.(float64); ok {
				numericID = int64(f)
			} else if i, ok := msg.ID.(int64); ok {
				numericID = i
			}

			c.pendingLock.Lock()
			ch, ok := c.pending[numericID]
			c.pendingLock.Unlock()

			if ok {
				ch <- &msg
			}
		}
	}

	// Jika scanner selesai (daemon keluar)
	c.pendingLock.Lock()
	for _, ch := range c.pending {
		close(ch)
	}
	c.pending = make(map[int64]chan *JSONRPCMessage)
	c.pendingLock.Unlock()

	c.Close()
}
