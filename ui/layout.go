package ui

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/autokeren/autokeren/ghost"
	"github.com/autokeren/autokeren/ipc"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// SpinnerTickMsg adalah tick untuk animasi spinner
type SpinnerTickMsg struct{}

// ActionFinishedMsg dikirim setelah panggilan RPC asinkron selesai
type ActionFinishedMsg struct {
	Action string
	Reply  interface{}
	Err    error
}

// StartupResumeMsg dikirim saat resume otomatis sewaktu startup selesai
type StartupResumeMsg struct {
	Status        StatusUpdateMsg
	ResumeMessage string
	RawMessages   interface{}
}

// PeriodicTickMsg adalah tick periodik untuk refresh status & ghost agents
type PeriodicTickMsg struct {
	Status      map[string]interface{}
	GhostAgents []*ghost.GhostAgentInfo
}

// Definisikan tipe-tipe pesan Bubble Tea untuk komunikasi asinkron dari daemon
type ChunkMsg struct{ Text string }
type ModelStartMsg struct{}
type ModelEndMsg struct {
	Content     string
	ModelID     string
	SessionID   string
	SessionName string
	Usage       map[string]interface{}
}
type ToolStartMsg struct {
	Name string
	Args map[string]interface{}
}
type ToolEndMsg struct {
	Name   string
	Result map[string]interface{}
}
type ToolOutputMsg struct {
	Name string
	Line string
}
type RetryMsg struct {
	Attempt int
	Delay   float64
	Message string
}
type ContextUpdateMsg struct {
	Tokens int
	Window int
}
type ErrorMsg struct{ Message string }
type ModelsLoadedMsg struct {
	Models []ModelSelectorItem
}
type SessionSavedMsg struct {
	SessionID   string
	SessionName string
}
type StatusUpdateMsg struct {
	ModelName        string
	ProjectName      string
	ContextUsed      int
	ContextWindow    int
	ContextPct       float64
	NeuronsRemaining int
	NeuronsQuota     int
	Todos            []TodoItem
	KanbanTasks      []KanbanTask
	Version          string
	SessionID        string
	SessionName      string
}

// PermissionConfirmReq mewakili request izin masuk yang harus direspon balik
type PermissionConfirmReq struct {
	Name        string
	Description string
	Arguments   map[string]interface{}
	RespChan    chan bool
}

// PermissionAbortMsg dikirim saat user memilih abort (q) pada dialog izin
type PermissionAbortMsg struct{}

type ModelSelectorItem struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	Active bool   `json:"active"`
}

type SlashCommandInfo struct {
	Name        string
	Description string
}

var slashCommands = []SlashCommandInfo{
	{Name: "/help", Description: "Tampilkan bantuan perintah slash"},
	{Name: "/model", Description: "Ganti model AI yang digunakan"},
	{Name: "/lang", Description: "Lihat atau ubah bahasa antarmuka"},
	{Name: "/permissions", Description: "Lihat status izin tool"},
	{Name: "/copy", Description: "Salin pesan terakhir atau pesan ke-N"},
	{Name: "/debug", Description: "Aktifkan/nonaktifkan mode debug"},
	{Name: "/memory", Description: "Tampilkan memory proyek"},
	{Name: "/status", Description: "Tampilkan status engine, model, dan proyek"},
	{Name: "/plan", Description: "Aktifkan atau nonaktifkan plan mode"},
	{Name: "/approve", Description: "Setujui rencana agar agen dapat melanjutkan"},
	{Name: "/project", Description: "Kelola pekerjaan multi-agent"},
	{Name: "/tdd", Description: "Minta agen menjalankan workflow test-driven development"},
	{Name: "/spec", Description: "Interview dan rencana implementasi"},
	{Name: "/genome", Description: "Scan struktur dan duplikasi codebase"},
	{Name: "/loop", Description: "Lihat atau pulihkan loop breaker model"},
	{Name: "/deploy", Description: "Minta agen membangun dan deploy aplikasi Cloudflare"},
	{Name: "/rewind", Description: "Kembalikan perubahan dari checkpoint"},
	{Name: "/review", Description: "Audit perubahan kode saat ini"},
	{Name: "/security", Description: "Scan keamanan proyek"},
	{Name: "/proof", Description: "Kelola bukti verifikasi rilis"},
	{Name: "/research", Description: "Lakukan riset web untuk tugas"},
	{Name: "/export", Description: "Ekspor percakapan ke Markdown"},
	{Name: "/ghost", Description: "Kelola background agent"},
	{Name: "/board", Description: "Buka/tutup papan Kanban proyek (Shortcut: Ctrl+K)"},
	{Name: "/kanban", Description: "Buka/tutup papan Kanban proyek (Shortcut: Ctrl+K)"},
	{Name: "/debate", Description: "Lihat visualisasi diskusi multi-agent (Shortcut: Ctrl+D)"},
	{Name: "/compact", Description: "Kompak/ringkas konteks percakapan"},
	{Name: "/reset", Description: "Reset sesi percakapan baru"},
	{Name: "/save", Description: "Simpan sesi percakapan aktif ke disk"},
	{Name: "/resume", Description: "Lanjutkan sesi percakapan yang disimpan"},
	{Name: "/sessions", Description: "Tampilkan semua sesi percakapan yang disimpan"},
	{Name: "/mcp", Description: "Kelola MCP server aktif (list/show/add)"},
	{Name: "/config", Description: "Lihat/ubah konfigurasi aktif"},
	{Name: "/local", Description: "Set/lihat local LLM endpoint (Ollama)"},
	{Name: "/approval", Description: "Set approval mode untuk tool"},
	{Name: "/q", Description: "Keluar dari autokeren"},
}

type MainModel struct {
	Chat        ChatModel
	Sidebar     SidebarModel
	TextInput   textinput.Model
	IPCClient   *ipc.Client
	GhostMgr    *ghost.GhostManager
	ProjectRoot string
	ConfigPath  string
	InitOpts    map[string]interface{}

	Width  int
	Height int

	AgentRunning  bool
	PermissionReq *PermissionConfirmReq
	ActiveModelID string

	Initialized       bool
	InitError         string
	ActiveEditingFile string

	ShowModelSelector  bool
	SelectorModels     []ModelSelectorItem
	SelectedModelIndex int

	ShowAutocomplete bool
	FilteredCmds     []SlashCommandInfo
	SelectedCommand  int

	// Spinner state
	SpinnerFrame int
	SpinnerDir   int // 1 = kanan, -1 = kiri (untuk bouncing ball)
	SpinnerPos   int // posisi bola saat ini

	// Always-allow set: tool name yang sudah diizinkan selama sesi
	AlwaysAllow   map[string]bool
	AllowAllTools bool // autonomous mode: semua tool diizinkan tanpa konfirmasi

	// Task aktif saat ini (ditampilkan di sidebar)
	CurrentTask string

	ShowKanban        bool
	KanbanTasks       []KanbanTask
	SelectedColumn    int // 0 = Todo, 1 = In Progress, 2 = Done
	SelectedTaskIndex int
	KanbanAddingTask  bool
	KanbanInputTitle  textinput.Model

	McpAddingServer     bool
	McpInputName        textinput.Model
	McpInputCmd         textinput.Model
	McpInputActiveField int // 0 = Name, 1 = Command

	ShowDebate            bool
	SelectedDebateAgentID int
}

type KanbanTask struct {
	ID          int    `json:"id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Status      string `json:"status"`
	Priority    string `json:"priority"`
	CreatedAt   string `json:"created_at"`
	UpdatedAt   string `json:"updated_at"`
}

func NewMainModel(client *ipc.Client, ghostMgr *ghost.GhostManager, projectRoot, configPath string, opts map[string]interface{}) MainModel {
	ti := textinput.New()
	ti.Placeholder = "Ketik perintah atau / untuk melihat menu..."
	ti.Focus()
	ti.CharLimit = 1000
	ti.Width = 80
	ti.Prompt = " ❯ "
	ti.PromptStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#00E5FF")).Bold(true)

	kit := textinput.New()
	kit.Placeholder = "Judul task baru..."
	kit.CharLimit = 200
	kit.Width = 50
	kit.Prompt = " ✏️  "
	kit.PromptStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)

	return MainModel{
		Chat:                  NewChatModel(),
		Sidebar:               NewSidebarModel(),
		TextInput:             ti,
		IPCClient:             client,
		GhostMgr:              ghostMgr,
		ProjectRoot:           projectRoot,
		ConfigPath:            configPath,
		InitOpts:              opts,
		ActiveEditingFile:     "",
		ShowModelSelector:     false,
		SelectorModels:        []ModelSelectorItem{},
		SelectedModelIndex:    0,
		ShowAutocomplete:      false,
		FilteredCmds:          []SlashCommandInfo{},
		SelectedCommand:       0,
		SpinnerFrame:          0,
		SpinnerDir:            1,
		SpinnerPos:            0,
		AlwaysAllow:           make(map[string]bool),
		CurrentTask:           "",
		ShowKanban:            false,
		KanbanTasks:           []KanbanTask{},
		SelectedColumn:        0,
		SelectedTaskIndex:     0,
		KanbanAddingTask:      false,
		KanbanInputTitle:      kit,
		ShowDebate:            false,
		SelectedDebateAgentID: 0,
		McpAddingServer:       false,
		McpInputName: func() textinput.Model {
			ti := textinput.New()
			ti.Placeholder = "misal: filesystem"
			ti.CharLimit = 100
			ti.Width = 30
			ti.Prompt = " "
			return ti
		}(),
		McpInputCmd: func() textinput.Model {
			ti := textinput.New()
			ti.Placeholder = "npx -y @modelcontextprotocol/server-filesystem /tmp"
			ti.CharLimit = 1000
			ti.Width = 60
			ti.Prompt = " "
			return ti
		}(),
		McpInputActiveField: 0,
	}
}

func (m MainModel) Init() tea.Cmd {
	return tea.Batch(
		textinput.Blink,
		m.connectToAgentCmd(),
		spinnerTick(),
		m.pollPeriodicCmd(),
	)
}

func spinnerTick() tea.Cmd {
	return tea.Tick(120*time.Millisecond, func(_ time.Time) tea.Msg {
		return SpinnerTickMsg{}
	})
}

func (m MainModel) pollPeriodicCmd() tea.Cmd {
	return tea.Tick(2*time.Second, func(t time.Time) tea.Msg {
		var statusReply map[string]interface{}
		_ = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)

		var ghostAgents []*ghost.GhostAgentInfo
		if m.GhostMgr != nil {
			m.GhostMgr.Refresh()
			ghostAgents = m.GhostMgr.ActiveList()
		}

		return PeriodicTickMsg{
			Status:      statusReply,
			GhostAgents: ghostAgents,
		}
	})
}

func (m MainModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.Width = msg.Width
		m.Height = msg.Height

		sidebarWidth := 30
		if m.Width > 90 {
			sidebarWidth = m.Width / 4
			if sidebarWidth > 40 {
				sidebarWidth = 40
			}
		}

		m.Sidebar.Width = sidebarWidth
		m.Sidebar.Height = m.Height

		chatWidth := m.Width - sidebarWidth
		m.Chat.Resize(chatWidth, m.Height-4) // kurangi ruang untuk input box

		m.TextInput.Width = chatWidth - 6

	case SpinnerTickMsg:
		m.SpinnerFrame++
		// Bounce logic untuk bola gliding
		m.SpinnerPos += m.SpinnerDir
		if m.SpinnerPos >= 18 {
			m.SpinnerDir = -1
		}
		if m.SpinnerPos <= 0 {
			m.SpinnerDir = 1
		}
		return m, spinnerTick()

	case ChunkMsg:
		m.Chat.AppendMessage("assistant", msg.Text)

	case ModelStartMsg:
		m.AgentRunning = true
		// Tidak menambah pesan "berpikir..." — cukup spinner di UI

	case ModelEndMsg:
		m.CurrentTask = ""
		m.Sidebar.CurrentTask = ""
		m.Chat.UpdateViewport()

		// Update info token di sidebar jika ada
		if msg.Usage != nil {
			if total, ok := msg.Usage["total"].(float64); ok {
				m.Sidebar.ContextUsed += int(total)
			}
		}
		if msg.ModelID != "" {
			m.Sidebar.ModelName = msg.ModelID
		}

	case SessionSavedMsg:
		if msg.SessionID != "" {
			m.Sidebar.SessionID = msg.SessionID
		}
		if msg.SessionName != "" {
			m.Sidebar.SessionName = msg.SessionName
		}

	case ActionFinishedMsg:
		m.AgentRunning = false
		m.CurrentTask = ""
		m.Sidebar.CurrentTask = ""
		m.Chat.UpdateViewport()

		if msg.Err != nil {
			m.Chat.AppendMessage("system", fmt.Sprintf("⚠ Operasi agen gagal: %v\n\nSesi tetap aktif. Coba kirim ulang pesan, atau gunakan /model untuk memilih model lain.", msg.Err))
			return m, nil
		}

		switch msg.Action {
		case "compact":
			if reply, ok := msg.Reply.(map[string]interface{}); ok {
				if msgStr, exists := reply["message"].(string); exists {
					m.Chat.AppendMessage("system", msgStr)
				}
			}
		case "reset":
			m.Chat.Messages = []ChatMessage{}
			m.Chat.AppendMessage("system", "Sesi berhasil direset.")
			m.Sidebar.SessionID = "default"
			m.Sidebar.SessionName = "default"
		case "save":
			if reply, ok := msg.Reply.(map[string]interface{}); ok {
				if msgStr, exists := reply["message"].(string); exists {
					m.Chat.AppendMessage("system", msgStr)
				}
				if sid, exists := reply["session_id"].(string); exists {
					m.Sidebar.SessionID = sid
				}
				if sname, exists := reply["name"].(string); exists {
					m.Sidebar.SessionName = sname
				}
			}
		case "resume":
			if reply, ok := msg.Reply.(map[string]interface{}); ok {
				if msgStr, exists := reply["message"].(string); exists {
					m.Chat.AppendMessage("system", msgStr)
				}
				if sid, exists := reply["session_id"].(string); exists {
					m.Sidebar.SessionID = sid
				}
				if sname, exists := reply["session_name"].(string); exists {
					m.Sidebar.SessionName = sname
				}
				if rawMsgs, exists := reply["messages"].([]interface{}); exists {
					m.Chat.Messages = sessionChatMessages(rawMsgs)
				}
			}
		case "sessions":
			if reply, ok := msg.Reply.(map[string]interface{}); ok {
				if rawSessions, exists := reply["sessions"].([]interface{}); exists {
					if len(rawSessions) == 0 {
						m.Chat.AppendMessage("system", "Belum ada saved session.")
					} else {
						var sb strings.Builder
						sb.WriteString("Saved Sessions:\n")
						for _, rawS := range rawSessions {
							if sObj, ok := rawS.(map[string]interface{}); ok {
								id, _ := sObj["id"].(string)
								name, _ := sObj["name"].(string)
								created, _ := sObj["created_at"].(string)
								msgCount, _ := sObj["message_count"].(float64)
								sb.WriteString(fmt.Sprintf("- %s (ID: %s) — %d pesan (%s)\n", name, id, int(msgCount), created))
							}
						}
						m.Chat.AppendMessage("system", sb.String())
					}
				}
			}
		case "run":
			if reply, ok := msg.Reply.(map[string]interface{}); ok {
				if modelID, exists := reply["model_id"].(string); exists && modelID == "system" {
					if content, exists := reply["content"].(string); exists {
						m.Chat.AppendMessage("system", content)
					}
				}
				if sid, exists := reply["session_id"].(string); exists && sid != "" && sid != "default" {
					m.Sidebar.SessionID = sid
				}
				if sname, exists := reply["session_name"].(string); exists && sname != "" && sname != "default" {
					m.Sidebar.SessionName = sname
				}
			}
		}

	case ToolStartMsg:
		if msg.Name == "write_file" || msg.Name == "patch_file" || msg.Name == "read_file" {
			filePath, _ := msg.Args["path"].(string)
			m.ActiveEditingFile = filePath
			var verb string
			switch msg.Name {
			case "write_file":
				verb = "write"
			case "patch_file":
				verb = "edit"
			default:
				verb = "read"
			}
			m.Chat.AppendMessage("tool", fmt.Sprintf("📝 %s\n  📂 Path: %s\n  ⚙ Status: working...", verb, filePath))
		} else {
			m.Chat.AppendMessage("tool", fmt.Sprintf("⏺ %s", msg.Name))
		}

	case ToolEndMsg:
		ok := true
		if val, exists := msg.Result["ok"]; exists {
			if b, isBool := val.(bool); isBool {
				ok = b
			}
		}
		if m.ActiveEditingFile != "" {
			if ok {
				m.Chat.AppendMessage("tool", fmt.Sprintf("✓ done\n  📂 Path: %s", m.ActiveEditingFile))
			} else {
				m.Chat.AppendMessage("tool", fmt.Sprintf("✗ failed\n  📂 Path: %s\n  ⚠ Error: %v", m.ActiveEditingFile, msg.Result["error"]))
			}
			m.ActiveEditingFile = ""
		} else {
			if ok {
				m.Chat.AppendMessage("tool", fmt.Sprintf("✓ %s", msg.Name))
			} else {
				m.Chat.AppendMessage("tool", fmt.Sprintf("✗ %s: %v", msg.Name, msg.Result["error"]))
			}
		}

	case ToolOutputMsg:
		m.Chat.AppendMessage("tool", fmt.Sprintf("│ %s", msg.Line))

	case RetryMsg:
		if msg.Attempt > 0 {
			m.Chat.AppendMessage("system", fmt.Sprintf("retry #%d (%.0fs) %s", msg.Attempt, msg.Delay, msg.Message))
		} else {
			m.Chat.AppendMessage("system", msg.Message)
		}

	case ContextUpdateMsg:
		m.Sidebar.ContextUsed = msg.Tokens
		if msg.Window > 0 {
			m.Sidebar.ContextWindow = msg.Window
			m.Sidebar.ContextPct = float64(msg.Tokens) / float64(msg.Window) * 100
		}

	case ErrorMsg:
		if !m.Initialized {
			m.InitError = msg.Message
			m.Chat.AppendMessage("system", fmt.Sprintf("error: %s", msg.Message))
			break
		}
		m.AgentRunning = false
		m.CurrentTask = ""
		m.Sidebar.CurrentTask = ""
		m.Chat.AppendMessage("system", fmt.Sprintf("⚠ Gangguan agen: %s\n\nSesi tetap aktif. Kamu bisa lanjut mengirim pesan atau mengganti model dengan /model.", msg.Message))

	case ModelsLoadedMsg:
		m.SelectorModels = msg.Models
		m.ShowModelSelector = true
		m.SelectedModelIndex = 0
		for i, item := range m.SelectorModels {
			if item.Active {
				m.SelectedModelIndex = i
				break
			}
		}

	case StatusUpdateMsg:
		m.Initialized = true
		m.Sidebar.ModelName = msg.ModelName
		m.Sidebar.ProjectName = msg.ProjectName
		m.Sidebar.ContextUsed = msg.ContextUsed
		m.Sidebar.ContextWindow = msg.ContextWindow
		m.Sidebar.ContextPct = msg.ContextPct
		m.Sidebar.NeuronsRemaining = msg.NeuronsRemaining
		m.Sidebar.NeuronsQuota = msg.NeuronsQuota
		m.Sidebar.Todos = msg.Todos
		m.KanbanTasks = msg.KanbanTasks
		m.Sidebar.Version = msg.Version
		m.Sidebar.SessionID = msg.SessionID
		m.Sidebar.SessionName = msg.SessionName

	case StartupResumeMsg:
		m.Initialized = true
		m.Sidebar.ModelName = msg.Status.ModelName
		m.Sidebar.ProjectName = msg.Status.ProjectName
		m.Sidebar.ContextUsed = msg.Status.ContextUsed
		m.Sidebar.ContextWindow = msg.Status.ContextWindow
		m.Sidebar.ContextPct = msg.Status.ContextPct
		m.Sidebar.NeuronsRemaining = msg.Status.NeuronsRemaining
		m.Sidebar.NeuronsQuota = msg.Status.NeuronsQuota
		m.Sidebar.Todos = msg.Status.Todos
		m.KanbanTasks = msg.Status.KanbanTasks
		m.Sidebar.Version = msg.Status.Version
		m.Sidebar.SessionID = msg.Status.SessionID
		m.Sidebar.SessionName = msg.Status.SessionName

		m.Chat.AppendMessage("system", msg.ResumeMessage)
		if rawMsgs, ok := msg.RawMessages.([]interface{}); ok {
			m.Chat.Messages = sessionChatMessages(rawMsgs)
		}
		m.Chat.UpdateViewportScroll(true)

	case PeriodicTickMsg:
		m.Sidebar.GhostAgents = msg.GhostAgents
		if msg.Status != nil {
			parsed := parseStatusReply(msg.Status, m.ProjectRoot)
			m.Sidebar.ModelName = parsed.ModelName
			m.Sidebar.ProjectName = parsed.ProjectName
			m.Sidebar.ContextUsed = parsed.ContextUsed
			m.Sidebar.ContextWindow = parsed.ContextWindow
			m.Sidebar.ContextPct = parsed.ContextPct
			m.Sidebar.NeuronsRemaining = parsed.NeuronsRemaining
			m.Sidebar.NeuronsQuota = parsed.NeuronsQuota
			m.Sidebar.Todos = parsed.Todos
			m.KanbanTasks = parsed.KanbanTasks
			m.Sidebar.Version = parsed.Version
			m.Sidebar.SessionID = parsed.SessionID
			m.Sidebar.SessionName = parsed.SessionName
		}
		return m, m.pollPeriodicCmd()

	case PermissionConfirmReq:
		// Autonomous mode: auto-approve tanpa dialog
		if m.AllowAllTools || m.AlwaysAllow[msg.Name] {
			msg.RespChan <- true
			return m, nil
		}
		m.PermissionReq = &msg

	case tea.KeyMsg:
		if m.McpAddingServer {
			switch msg.String() {
			case "esc":
				m.McpAddingServer = false
				m.McpInputName.SetValue("")
				m.McpInputCmd.SetValue("")
				m.McpInputActiveField = 0
				m.TextInput.Focus()
				return m, nil
			case "tab", "up", "down":
				if m.McpInputActiveField == 0 {
					m.McpInputActiveField = 1
					m.McpInputCmd.Focus()
					m.McpInputName.Blur()
				} else {
					m.McpInputActiveField = 0
					m.McpInputName.Focus()
					m.McpInputCmd.Blur()
				}
				return m, nil
			case "enter":
				if m.McpInputActiveField == 0 {
					m.McpInputActiveField = 1
					m.McpInputCmd.Focus()
					m.McpInputName.Blur()
					return m, nil
				} else {
					name := strings.TrimSpace(m.McpInputName.Value())
					cmdRaw := strings.TrimSpace(m.McpInputCmd.Value())
					if name != "" && cmdRaw != "" {
						m.McpAddingServer = false
						m.McpInputName.SetValue("")
						m.McpInputCmd.SetValue("")
						m.McpInputActiveField = 0
						m.TextInput.Focus()

						// Kirim ke daemon untuk dijalankan
						m.AgentRunning = true
						m.CurrentTask = "Menambahkan MCP server..."
						m.Sidebar.CurrentTask = "Menambahkan MCP server..."
						runCmd := func() tea.Msg {
							runParams := map[string]interface{}{
								"user_input": fmt.Sprintf("/mcp add %s %s", name, cmdRaw),
							}
							var reply map[string]interface{}
							err := m.IPCClient.Call("agent.run", runParams, &reply)
							return ActionFinishedMsg{Action: "run", Reply: reply, Err: err}
						}
						return m, runCmd
					}
				}
				return m, nil
			default:
				var cmd tea.Cmd
				if m.McpInputActiveField == 0 {
					m.McpInputName, cmd = m.McpInputName.Update(msg)
				} else {
					m.McpInputCmd, cmd = m.McpInputCmd.Update(msg)
				}
				return m, cmd
			}
		}

		if m.ShowDebate {
			switch msg.String() {
			case "tab", "esc", "ctrl+d":
				m.ShowDebate = false
				m.TextInput.Focus()
				return m, nil
			case "left", "h":
				list := m.GhostMgr.List()
				if len(list) > 0 {
					idx := -1
					for i, a := range list {
						if a.ID == m.SelectedDebateAgentID {
							idx = i
							break
						}
					}
					if idx == -1 {
						m.SelectedDebateAgentID = list[0].ID
					} else {
						idx--
						if idx < 0 {
							idx = len(list) - 1
						}
						m.SelectedDebateAgentID = list[idx].ID
					}
				}
				return m, nil
			case "right", "l":
				list := m.GhostMgr.List()
				if len(list) > 0 {
					idx := -1
					for i, a := range list {
						if a.ID == m.SelectedDebateAgentID {
							idx = i
							break
						}
					}
					if idx == -1 {
						m.SelectedDebateAgentID = list[0].ID
					} else {
						idx++
						if idx >= len(list) {
							idx = 0
						}
						m.SelectedDebateAgentID = list[idx].ID
					}
				}
				return m, nil
			case "k":
				if m.SelectedDebateAgentID != 0 {
					m.GhostMgr.Kill(m.SelectedDebateAgentID)
					list := m.GhostMgr.List()
					if len(list) > 0 {
						m.SelectedDebateAgentID = list[0].ID
					} else {
						m.SelectedDebateAgentID = 0
					}
				}
				return m, nil
			}
			return m, nil
		}

		if m.ShowKanban {
			if m.KanbanAddingTask {
				switch msg.String() {
				case "enter":
					val := m.KanbanInputTitle.Value()
					if val != "" {
						var reply map[string]interface{}
						_ = m.IPCClient.Call("kanban.add", map[string]interface{}{
							"title":    val,
							"status":   "todo",
							"priority": "medium",
						}, &reply)

						// Ambil status terbaru
						var statusReply map[string]interface{}
						_ = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
						parsed := parseStatusReply(statusReply, m.ProjectRoot)
						m.KanbanTasks = parsed.KanbanTasks
						m.Sidebar.Todos = parsed.Todos
					}
					m.KanbanAddingTask = false
					m.KanbanInputTitle.SetValue("")
					m.SelectedTaskIndex = 0
					return m, nil
				case "esc":
					m.KanbanAddingTask = false
					m.KanbanInputTitle.SetValue("")
					return m, nil
				default:
					var cmd tea.Cmd
					m.KanbanInputTitle, cmd = m.KanbanInputTitle.Update(msg)
					return m, cmd
				}
			}

			switch msg.String() {
			case "tab", "esc", "ctrl+k":
				m.ShowKanban = false
				m.TextInput.Focus()
				return m, nil
			case "left", "h":
				m.SelectedColumn--
				if m.SelectedColumn < 0 {
					m.SelectedColumn = 2
				}
				m.SelectedTaskIndex = 0
				return m, nil
			case "right", "l":
				m.SelectedColumn++
				if m.SelectedColumn > 2 {
					m.SelectedColumn = 0
				}
				m.SelectedTaskIndex = 0
				return m, nil
			case "up", "k":
				m.SelectedTaskIndex--
				if m.SelectedTaskIndex < 0 {
					m.SelectedTaskIndex = 0
				}
				return m, nil
			case "down", "j":
				m.SelectedTaskIndex++
				var colTasksCount int
				status := "todo"
				if m.SelectedColumn == 1 {
					status = "in_progress"
				} else if m.SelectedColumn == 2 {
					status = "done"
				}
				for _, t := range m.KanbanTasks {
					if t.Status == status {
						colTasksCount++
					}
				}
				if m.SelectedTaskIndex >= colTasksCount {
					m.SelectedTaskIndex = colTasksCount - 1
					if m.SelectedTaskIndex < 0 {
						m.SelectedTaskIndex = 0
					}
				}
				return m, nil
			case "space":
				if task, ok := m.getSelectedTask(); ok {
					nextStatus := "in_progress"
					if task.Status == "in_progress" {
						nextStatus = "done"
					} else if task.Status == "done" {
						nextStatus = "todo"
					}
					var reply map[string]interface{}
					_ = m.IPCClient.Call("kanban.move", map[string]interface{}{
						"id":     task.ID,
						"status": nextStatus,
					}, &reply)

					// Refresh
					var statusReply map[string]interface{}
					_ = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
					parsed := parseStatusReply(statusReply, m.ProjectRoot)
					m.KanbanTasks = parsed.KanbanTasks
					m.Sidebar.Todos = parsed.Todos
					m.SelectedTaskIndex = 0
				}
				return m, nil
			case "a", "n":
				m.KanbanAddingTask = true
				m.KanbanInputTitle.SetValue("")
				m.KanbanInputTitle.Focus()
				return m, nil
			case "d", "x":
				if task, ok := m.getSelectedTask(); ok {
					var reply map[string]interface{}
					_ = m.IPCClient.Call("kanban.delete", map[string]interface{}{
						"id": task.ID,
					}, &reply)

					// Refresh
					var statusReply map[string]interface{}
					_ = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
					parsed := parseStatusReply(statusReply, m.ProjectRoot)
					m.KanbanTasks = parsed.KanbanTasks
					m.Sidebar.Todos = parsed.Todos
					m.SelectedTaskIndex = 0
				}
				return m, nil
			}
			return m, nil
		}

		// Jika autocomplete slash sedang tampil, tangani navigasi dropdown dulu
		if m.ShowAutocomplete && len(m.FilteredCmds) > 0 {
			switch msg.String() {
			case "up", "shift+tab":
				m.SelectedCommand--
				if m.SelectedCommand < 0 {
					m.SelectedCommand = len(m.FilteredCmds) - 1
				}
				return m, nil
			case "down", "tab":
				m.SelectedCommand++
				if m.SelectedCommand >= len(m.FilteredCmds) {
					m.SelectedCommand = 0
				}
				return m, nil
			case "enter":
				selected := m.FilteredCmds[m.SelectedCommand]
				m.ShowAutocomplete = false
				m.TextInput.SetValue(selected.Name + " ")
				m.TextInput.CursorEnd()
				// Langsung trigger action kalau command lengkap (tanpa argumen)
				if selected.Name == "/model" {
					m.TextInput.SetValue("")
					m.Chat.AppendMessage("system", "Memuat daftar model...")
					return m, m.fetchModelsCmd()
				}
				if selected.Name == "/compact" {
					m.TextInput.SetValue("")
					m.AgentRunning = true
					m.Chat.AppendMessage("system", "Mengompak context...")
					cmd := func() tea.Msg {
						var reply map[string]interface{}
						err := m.IPCClient.Call("agent.compact", map[string]interface{}{}, &reply)
						return ActionFinishedMsg{Action: "compact", Reply: reply, Err: err}
					}
					return m, cmd
				}
				if selected.Name == "/reset" {
					m.TextInput.SetValue("")
					m.AgentRunning = true
					m.Chat.AppendMessage("system", "Mereset sesi percakapan...")
					cmd := func() tea.Msg {
						var reply string
						err := m.IPCClient.Call("agent.reset", map[string]interface{}{}, &reply)
						return ActionFinishedMsg{Action: "reset", Reply: reply, Err: err}
					}
					return m, cmd
				}
				if selected.Name == "/q" {
					m.IPCClient.Close()
					return m, tea.Quit
				}
				// Untuk /ghost: biarkan user isi argumen setelah
				return m, nil
			case "esc":
				m.ShowAutocomplete = false
				m.TextInput.SetValue("")
				return m, nil
			default:
				// Shortcut angka 1-9 langsung pilih
				if len(msg.String()) == 1 && msg.String() >= "1" && msg.String() <= "9" {
					idx := int(msg.String()[0] - '1')
					if idx >= 0 && idx < len(m.FilteredCmds) {
						selected := m.FilteredCmds[idx]
						m.ShowAutocomplete = false
						if selected.Name == "/model" {
							m.TextInput.SetValue("")
							m.Chat.AppendMessage("system", "Memuat daftar model...")
							return m, m.fetchModelsCmd()
						}
						if selected.Name == "/q" {
							m.IPCClient.Close()
							return m, tea.Quit
						}
						m.TextInput.SetValue(selected.Name + " ")
						m.TextInput.CursorEnd()
						return m, nil
					}
				}
			}
		}

		// Jika selector model sedang tampil, tangani navigasi selector model
		if m.ShowModelSelector {
			switch msg.String() {
			case "up", "shift+tab":
				m.SelectedModelIndex--
				if m.SelectedModelIndex < 0 {
					m.SelectedModelIndex = len(m.SelectorModels) - 1
				}
				return m, nil
			case "down", "tab":
				m.SelectedModelIndex++
				if m.SelectedModelIndex >= len(m.SelectorModels) {
					m.SelectedModelIndex = 0
				}
				return m, nil
			case "enter":
				if len(m.SelectorModels) > 0 {
					selected := m.SelectorModels[m.SelectedModelIndex]
					m.ShowModelSelector = false
					m.Chat.AppendMessage("system", fmt.Sprintf("Mengganti model ke: %s...", selected.Name))
					return m, m.switchModelCmd(selected.ID)
				}
				return m, nil
			case "esc":
				m.ShowModelSelector = false
				return m, nil
			default:
				// Shortcut keyboard angka (1-9)
				if len(msg.String()) == 1 && msg.String() >= "1" && msg.String() <= "9" {
					idx := int(msg.String()[0] - '1')
					if idx >= 0 && idx < len(m.SelectorModels) {
						selected := m.SelectorModels[idx]
						m.ShowModelSelector = false
						m.Chat.AppendMessage("system", fmt.Sprintf("Mengganti model ke: %s...", selected.Name))
						return m, m.switchModelCmd(selected.ID)
					}
				}
			}
			return m, nil
		}

		// Jika dialog izin sedang aktif, tangani 4 opsi
		if m.PermissionReq != nil {
			switch msg.String() {
			case "y", "Y", "enter":
				m.PermissionReq.RespChan <- true
				m.PermissionReq = nil
			case "a", "A":
				m.AlwaysAllow[m.PermissionReq.Name] = true
				m.PermissionReq.RespChan <- true
				m.PermissionReq = nil
			case "t", "T":
				m.AllowAllTools = true
				m.PermissionReq.RespChan <- true
				m.PermissionReq = nil
				m.Chat.AppendMessage("system", "⚡ autonomous mode: semua tool diizinkan untuk sesi ini")
			case "n", "N", "esc":
				m.PermissionReq.RespChan <- false
				m.Chat.AppendMessage("system", fmt.Sprintf("✗ denied: %s", m.PermissionReq.Name))
				m.PermissionReq = nil
			case "q", "Q":
				m.PermissionReq.RespChan <- false
				m.PermissionReq = nil
				m.AgentRunning = false
				m.Chat.AppendMessage("system", "task aborted.")
			}
			return m, nil
		}

		switch msg.Type {
		case tea.KeyCtrlK:
			m.ShowKanban = !m.ShowKanban
			if m.ShowKanban {
				m.ShowDebate = false
				m.SelectedColumn = 0
				m.SelectedTaskIndex = 0
				var statusReply map[string]interface{}
				_ = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
				parsed := parseStatusReply(statusReply, m.ProjectRoot)
				m.KanbanTasks = parsed.KanbanTasks
				m.Sidebar.Todos = parsed.Todos
			} else {
				m.TextInput.Focus()
			}
			return m, nil

		case tea.KeyCtrlD:
			m.ShowDebate = !m.ShowDebate
			if m.ShowDebate {
				m.ShowKanban = false
				list := m.GhostMgr.List()
				if len(list) > 0 {
					m.SelectedDebateAgentID = list[0].ID
				} else {
					m.SelectedDebateAgentID = 0
				}
			} else {
				m.TextInput.Focus()
			}
			return m, nil

		case tea.KeyCtrlC:
			if m.AgentRunning {
				go func() {
					var reply string
					_ = m.IPCClient.Call("agent.interrupt", map[string]interface{}{}, &reply)
				}()
				m.Chat.AppendMessage("system", "Interupsi dikirim ke agen...")
			} else {
				m.Chat.AppendMessage("system", "Agen sedang diam. Gunakan /q atau Ctrl+Q untuk keluar.")
			}
			return m, nil

		case tea.KeyCtrlQ:
			m.IPCClient.Close()
			return m, tea.Quit

		case tea.KeyEnter:
			val := strings.TrimSpace(m.TextInput.Value())
			if val == "" {
				return m, nil
			}

			if val == "/q" || val == "/quit" {
				m.IPCClient.Close()
				return m, tea.Quit
			}

			m.TextInput.SetValue("")
			m.Chat.AppendMessage("user", val)

			// ── Penanganan Slash Commands Secara Native ────────────────────
			if val == "/mcp add" {
				m.McpAddingServer = true
				m.McpInputName.SetValue("")
				m.McpInputCmd.SetValue("")
				m.McpInputActiveField = 0
				m.McpInputName.Focus()
				m.McpInputCmd.Blur()
				return m, nil
			}

			if strings.HasPrefix(val, "/ghost") {
				args := strings.TrimSpace(strings.TrimPrefix(val, "/ghost"))
				m.handleGhostCommand(args)
				return m, nil
			}

			if strings.HasPrefix(val, "/model") {
				args := strings.TrimSpace(strings.TrimPrefix(val, "/model"))
				if args == "" {
					m.TextInput.SetValue("")
					m.Chat.AppendMessage("system", "Memuat daftar model...")
					return m, m.fetchModelsCmd()
				} else {
					m.TextInput.SetValue("")
					m.Chat.AppendMessage("system", fmt.Sprintf("Mengganti model ke: %s...", args))
					return m, m.switchModelCmd(args)
				}
			}

			if strings.HasPrefix(val, "/approval") {
				args := strings.TrimSpace(strings.TrimPrefix(val, "/approval"))
				m.TextInput.SetValue("")
				switch args {
				case "all":
					m.AllowAllTools = true
					m.Chat.AppendMessage("system", "Approval mode: semua tool diizinkan untuk sesi ini.")
				case "ask", "default", "":
					m.AllowAllTools = false
					m.Chat.AppendMessage("system", "Approval mode: tool berisiko akan meminta izin.")
				default:
					m.Chat.AppendMessage("system", "Gunakan: /approval ask atau /approval all")
				}
				return m, nil
			}

			if val == "/permissions" {
				if m.AllowAllTools {
					m.Chat.AppendMessage("system", "Semua tool diizinkan untuk sesi ini.")
				} else if len(m.AlwaysAllow) > 0 {
					names := make([]string, 0, len(m.AlwaysAllow))
					for name := range m.AlwaysAllow {
						names = append(names, name)
					}
					sort.Strings(names)
					m.Chat.AppendMessage("system", "Tool diizinkan: "+strings.Join(names, ", "))
				} else {
					m.Chat.AppendMessage("system", "Belum ada tool yang diizinkan. Tool berisiko akan meminta izin.")
				}
				return m, nil
			}

			if val == "/compact" {
				m.AgentRunning = true
				m.Chat.AppendMessage("system", "Mengompak context...")
				cmd := func() tea.Msg {
					var reply map[string]interface{}
					err := m.IPCClient.Call("agent.compact", map[string]interface{}{}, &reply)
					return ActionFinishedMsg{Action: "compact", Reply: reply, Err: err}
				}
				return m, cmd
			}

			if val == "/reset" {
				m.AgentRunning = true
				m.Chat.AppendMessage("system", "Mereset sesi percakapan...")
				cmd := func() tea.Msg {
					var reply string
					err := m.IPCClient.Call("agent.reset", map[string]interface{}{}, &reply)
					return ActionFinishedMsg{Action: "reset", Reply: reply, Err: err}
				}
				return m, cmd
			}

			if strings.HasPrefix(val, "/save") {
				args := strings.TrimSpace(strings.TrimPrefix(val, "/save"))
				m.AgentRunning = true
				m.TextInput.SetValue("")
				m.Chat.AppendMessage("system", fmt.Sprintf("Menyimpan sesi %s...", args))
				cmd := func() tea.Msg {
					var reply map[string]interface{}
					params := map[string]interface{}{}
					if args != "" {
						params["name"] = args
					}
					err := m.IPCClient.Call("agent.save_session", params, &reply)
					return ActionFinishedMsg{Action: "save", Reply: reply, Err: err}
				}
				return m, cmd
			}

			if strings.HasPrefix(val, "/resume") {
				args := strings.TrimSpace(strings.TrimPrefix(val, "/resume"))
				m.TextInput.SetValue("")
				if args == "" {
					m.Chat.AppendMessage("system", "Gunakan: /resume <id_atau_nama_session>")
					return m, nil
				}
				m.AgentRunning = true
				m.Chat.AppendMessage("system", fmt.Sprintf("Meresume sesi %s...", args))
				cmd := func() tea.Msg {
					var reply map[string]interface{}
					params := map[string]interface{}{"identifier": args}
					err := m.IPCClient.Call("agent.resume_session", params, &reply)
					return ActionFinishedMsg{Action: "resume", Reply: reply, Err: err}
				}
				return m, cmd
			}

			if val == "/sessions" {
				m.AgentRunning = true
				m.TextInput.SetValue("")
				m.Chat.AppendMessage("system", "Memuat daftar sesi...")
				cmd := func() tea.Msg {
					var reply map[string]interface{}
					err := m.IPCClient.Call("agent.list_sessions", map[string]interface{}{}, &reply)
					return ActionFinishedMsg{Action: "sessions", Reply: reply, Err: err}
				}
				return m, cmd
			}

			if val == "/board" || val == "/kanban" {
				m.ShowKanban = !m.ShowKanban
				if m.ShowKanban {
					m.SelectedColumn = 0
					m.SelectedTaskIndex = 0
					var statusReply map[string]interface{}
					_ = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
					parsed := parseStatusReply(statusReply, m.ProjectRoot)
					m.KanbanTasks = parsed.KanbanTasks
					m.Sidebar.Todos = parsed.Todos
				} else {
					m.TextInput.Focus()
				}
				return m, nil
			}

			if val == "/debate" {
				m.ShowDebate = !m.ShowDebate
				if m.ShowDebate {
					m.ShowKanban = false
					list := m.GhostMgr.List()
					if len(list) > 0 {
						m.SelectedDebateAgentID = list[0].ID
					} else {
						m.SelectedDebateAgentID = 0
					}
				} else {
					m.TextInput.Focus()
				}
				return m, nil
			}

			// ── Kirim perintah biasa secara asinkron ke background thread ──
			m.AgentRunning = true
			// Simpan ringkasan task di sidebar (maks 40 char)
			taskLabel := val
			if len([]rune(taskLabel)) > 40 {
				taskLabel = string([]rune(taskLabel)[:39]) + "…"
			}
			m.CurrentTask = taskLabel
			m.Sidebar.CurrentTask = taskLabel
			runCmd := func() tea.Msg {
				runParams := map[string]interface{}{
					"user_input": val,
				}
				var reply map[string]interface{}
				err := m.IPCClient.Call("agent.run", runParams, &reply)
				return ActionFinishedMsg{Action: "run", Reply: reply, Err: err}
			}

			return m, runCmd
		}
	}

	// Forward scroll keys ke Chat.Viewport (pgup/pgdn/up/down saat tidak typing)
	if keyMsg, ok := msg.(tea.KeyMsg); ok {
		switch keyMsg.String() {
		case "pgup", "ctrl+b":
			m.Chat.Viewport, _ = m.Chat.Viewport.Update(msg)
			return m, nil
		case "pgdown", "ctrl+f":
			m.Chat.Viewport, _ = m.Chat.Viewport.Update(msg)
			return m, nil
		case "up":
			if !m.ShowAutocomplete && !m.ShowModelSelector && m.PermissionReq == nil {
				m.Chat.Viewport, _ = m.Chat.Viewport.Update(msg)
				return m, nil
			}
		case "down":
			if !m.ShowAutocomplete && !m.ShowModelSelector && m.PermissionReq == nil {
				m.Chat.Viewport, _ = m.Chat.Viewport.Update(msg)
				return m, nil
			}
		}
	}

	if m.PermissionReq == nil {
		m.TextInput, cmd = m.TextInput.Update(msg)
	}

	// Cek apakah perlu tampilkan/update autocomplete berdasarkan isi text input
	if !m.ShowModelSelector && !m.AgentRunning {
		currentVal := m.TextInput.Value()
		if strings.HasPrefix(currentVal, "/") && !strings.Contains(currentVal, " ") {
			// Filter slash commands berdasarkan teks yang sudah diketik
			var filtered []SlashCommandInfo
			for _, sc := range slashCommands {
				if strings.HasPrefix(sc.Name, currentVal) {
					filtered = append(filtered, sc)
				}
			}
			m.FilteredCmds = filtered
			m.ShowAutocomplete = len(filtered) > 0
			if m.SelectedCommand >= len(filtered) {
				m.SelectedCommand = 0
			}
		} else {
			m.ShowAutocomplete = false
			m.FilteredCmds = nil
		}
	}

	return m, cmd
}

func (m MainModel) View() string {
	if m.Width == 0 || m.Height == 0 {
		return "Menginisialisasi antarmuka..."
	}

	if !m.Initialized && m.InitError == "" {
		sidebarView := m.Sidebar.View()
		chatWidth := m.Width - m.Sidebar.Width
		chatHeight := m.Height - 4

		chatStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#2A2A35")).
			Padding(1, 2).
			Width(chatWidth - 4).
			Height(chatHeight - 2)

		chatView := chatStyle.Render("⚙ Menghubungkan ke agen di latar belakang...\nHarap tunggu sebentar...")

		inputView := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#2A2A35")).
			Padding(0, 1).
			Width(chatWidth - 4).
			Render("Menghubungkan...")

		return lipgloss.JoinHorizontal(
			lipgloss.Top,
			sidebarView,
			lipgloss.JoinVertical(
				lipgloss.Left,
				chatView,
				inputView,
			),
		)
	}

	if m.InitError != "" {
		sidebarView := m.Sidebar.View()
		chatWidth := m.Width - m.Sidebar.Width
		chatHeight := m.Height - 4

		chatStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#FF5252")).
			Padding(1, 2).
			Width(chatWidth - 4).
			Height(chatHeight - 2)

		chatView := chatStyle.Render(fmt.Sprintf("⚠ GAGAL MENYAMBUNG KE AGEN:\n\n%s\n\nTekan [Ctrl+C] atau [Ctrl+Q] untuk keluar.", m.InitError))

		inputView := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#FF5252")).
			Padding(0, 1).
			Width(chatWidth - 4).
			Render("Gagal Inisialisasi")

		return lipgloss.JoinHorizontal(
			lipgloss.Top,
			sidebarView,
			lipgloss.JoinVertical(
				lipgloss.Left,
				chatView,
				inputView,
			),
		)
	}

	sidebarView := m.Sidebar.View()
	panelWidth := m.Width - m.Sidebar.Width - 4

	if m.ShowKanban {
		kanbanView := m.KanbanView(panelWidth, m.Height)
		return lipgloss.JoinHorizontal(
			lipgloss.Top,
			sidebarView,
			kanbanView,
		)
	}

	if m.ShowDebate {
		debateView := m.DebateView(panelWidth, m.Height)
		return lipgloss.JoinHorizontal(
			lipgloss.Top,
			sidebarView,
			debateView,
		)
	}

	inputStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#2A2A35")).
		Padding(0, 1).
		Width(panelWidth)

	inputView := inputStyle.Render(m.TextInput.View())

	// Bouncing ball gliding spinner
	var spinnerView string
	if m.AgentRunning && m.PermissionReq == nil {
		spinnerStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#1E1E2A")).
			Padding(0, 2).
			Width(panelWidth)

		// Track width untuk ball (kurangi padding + border)
		trackW := panelWidth - 10
		if trackW < 8 {
			trackW = 8
		}
		pos := m.SpinnerPos
		if pos > trackW {
			pos = trackW
		}

		// Gradient warna: kiri biru, tengah cyan, kanan ungu
		gradColors := []string{
			"#1E3A5F", "#1E4A8F", "#1560BD", "#0078D4",
			"#00A8E8", "#38BDF8", "#00E5FF", "#7C3AED",
		}

		var trackSb strings.Builder
		for i := 0; i < trackW; i++ {
			if i == pos {
				// Bola: bright white dot
				ballColor := gradColors[(i*len(gradColors))/trackW]
				trackSb.WriteString(
					lipgloss.NewStyle().Foreground(lipgloss.Color(ballColor)).Bold(true).Render("●"),
				)
			} else {
				// Track: titik redup
				trackSb.WriteString(
					lipgloss.NewStyle().Foreground(lipgloss.Color("#1E1E2A")).Render("─"),
				)
			}
		}

		labelStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#374151"))
		spinnerText := trackSb.String() + "  " + labelStyle.Render("processing")
		spinnerView = spinnerStyle.Render(spinnerText)
	}

	// Permission dialog overlay
	var permissionView string
	if m.PermissionReq != nil {
		permStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#FBBF24")).
			Padding(1, 3).
			Width(panelWidth)

		titleStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)
		toolStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#F8FAFC")).Bold(true)
		descStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280")).Italic(true)
		divStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#2D3748"))
		keyStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)
		keyBgStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FBBF24")).
			Background(lipgloss.Color("#1A1A2E")).
			Bold(true).
			Padding(0, 1)
		labelStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#94A3B8"))
		autoStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#A78BFA")).Bold(true)

		var pb strings.Builder
		pb.WriteString(titleStyle.Render("⚠  permission required") + "\n")
		pb.WriteString(divStyle.Render(strings.Repeat("─", panelWidth-10)) + "\n\n")
		pb.WriteString(toolStyle.Render("  "+m.PermissionReq.Name) + "\n")
		if m.PermissionReq.Description != "" {
			pb.WriteString(descStyle.Render("  "+m.PermissionReq.Description) + "\n")
		}
		pb.WriteString("\n")
		pb.WriteString(
			keyBgStyle.Render("y") + labelStyle.Render(" once") + "   " +
				keyBgStyle.Render("a") + labelStyle.Render(" this tool") + "   " +
				keyBgStyle.Render("t") + autoStyle.Render(" all tools") + "   " +
				keyStyle.Render("n") + labelStyle.Render(" deny") + "   " +
				keyStyle.Render("q") + labelStyle.Render(" abort"),
		)
		permissionView = permStyle.Render(pb.String())
	}

	// Render autocomplete slash command dropdown
	var autocompleteView string
	if m.ShowAutocomplete && len(m.FilteredCmds) > 0 {
		var acSb strings.Builder
		acStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#7C3AED")).
			Padding(0, 1).
			Width(panelWidth)

		titleStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#A78BFA")).Bold(true)
		acSb.WriteString(titleStyle.Render("  ╱ PERINTAH SLASH") + "\n")
		for i, sc := range m.FilteredCmds {
			numStr := fmt.Sprintf(" %d ", i+1)
			if i == m.SelectedCommand {
				selStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FFFFFF")).Background(lipgloss.Color("#7C3AED")).Bold(true)
				descStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#DDD6FE")).Background(lipgloss.Color("#4C1D95"))
				acSb.WriteString(selStyle.Render(fmt.Sprintf(" ▸%s%-12s", numStr, sc.Name)) + descStyle.Render(fmt.Sprintf(" %s ", sc.Description)) + "\n")
			} else {
				numStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280"))
				cmdStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#C4B5FD")).Bold(true)
				descStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280"))
				acSb.WriteString(numStyle.Render(fmt.Sprintf("  %s", numStr)) + cmdStyle.Render(fmt.Sprintf("%-12s", sc.Name)) + descStyle.Render(fmt.Sprintf(" %s", sc.Description)) + "\n")
			}
		}
		acSb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#4B5563")).Render("   ↑↓/Tab navigasi · Enter pilih · 1-5 cepat · Esc batal"))
		autocompleteView = acStyle.Render(acSb.String())
	}

	// Render Model Selector overlay jika aktif
	var modelSelectorView string
	if m.ShowModelSelector {
		var msSb strings.Builder
		msStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#00E5FF")).
			Padding(1, 2).
			Width(panelWidth)

		msSb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#00E5FF")).Bold(true).Render("🤖 PILIH MODEL KECERDASAN BUATAN:") + "\n\n")
		start, end := 0, len(m.SelectorModels)
		maxVisible := 5
		if end-start > maxVisible {
			start = m.SelectedModelIndex - maxVisible/2
			if start < 0 {
				start = 0
			}
			if start+maxVisible > end {
				start = end - maxVisible
			}
			end = start + maxVisible
		}
		if start > 0 {
			msSb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#888899")).Render("   ↑ model sebelumnya") + "\n")
		}
		for i := start; i < end; i++ {
			item := m.SelectorModels[i]
			numStr := fmt.Sprintf("%d. ", i+1)
			activeMarker := ""
			if item.Active {
				activeMarker = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FF66")).Render(" ✓ Aktif")
			}
			if i == m.SelectedModelIndex {
				msSb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#00E5FF")).Background(lipgloss.Color("#003344")).Bold(true).Render(fmt.Sprintf(" ▸ %s%-35s%s", numStr, item.Name, activeMarker)) + "\n")
			} else {
				msSb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#E0E0E0")).Render(fmt.Sprintf("   %s%-35s%s", numStr, item.Name, activeMarker)) + "\n")
			}
		}
		if end < len(m.SelectorModels) {
			msSb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#888899")).Render("   ↓ model berikutnya") + "\n")
		}
		msSb.WriteString("\n" + lipgloss.NewStyle().Foreground(lipgloss.Color("#888899")).Render("  ↑↓/Tab navigasi · Enter pilih · Esc batal · 1-9 pilih cepat"))
		modelSelectorView = msStyle.Render(msSb.String())
	}

	// Hitung tinggi komponen lain untuk menghitung sisa tinggi viewport chat secara dinamis
	otherHeights := 0

	// TextInput ditampilkan di semua keadaan kecuali saat agen berjalan dan tidak ada permission request
	showInput := true
	if m.AgentRunning && m.PermissionReq == nil {
		showInput = false
	}

	if showInput {
		otherHeights += 3 // Tinggi inputView (1 line input + 2 lines border)
	}

	if m.AgentRunning && m.PermissionReq == nil && spinnerView != "" {
		otherHeights += 3 // Tinggi spinnerView (1 line progress + 2 lines border)
	}

	if m.PermissionReq != nil {
		otherHeights += lipgloss.Height(permissionView)
	}

	if m.ShowModelSelector {
		otherHeights += lipgloss.Height(modelSelectorView)
	}

	if m.ShowAutocomplete && autocompleteView != "" {
		otherHeights += lipgloss.Height(autocompleteView)
	}

	var mcpDialogView string
	if m.McpAddingServer {
		mcpDialogView = renderMcpAddDialog(m.McpInputName, m.McpInputCmd, m.McpInputActiveField, panelWidth)
		otherHeights += lipgloss.Height(mcpDialogView)
	}

	// Tinggi viewport = Total tinggi terminal - tinggi komponen lain - border chat (2)
	vpHeight := m.Height - otherHeights - 2
	if vpHeight < 4 {
		vpHeight = 4
	}

	// Update tinggi viewport chat secara real-time
	m.Chat.Viewport.Height = vpHeight
	m.Chat.UpdateViewport()
	chatView := m.Chat.View()

	var rightPanel string
	switch {
	case m.ShowModelSelector:
		rightPanel = lipgloss.JoinVertical(
			lipgloss.Left,
			modelSelectorView,
			inputView,
		)
	case m.PermissionReq != nil:
		rightPanel = lipgloss.JoinVertical(
			lipgloss.Left,
			chatView,
			permissionView,
			inputView,
		)
	case m.AgentRunning && spinnerView != "":
		rightPanel = lipgloss.JoinVertical(
			lipgloss.Left,
			chatView,
			spinnerView,
		)
	case m.ShowAutocomplete && autocompleteView != "":
		rightPanel = lipgloss.JoinVertical(
			lipgloss.Left,
			chatView,
			autocompleteView,
			inputView,
		)
	case m.McpAddingServer:
		rightPanel = lipgloss.JoinVertical(
			lipgloss.Left,
			chatView,
			mcpDialogView,
			inputView,
		)
	default:
		rightPanel = lipgloss.JoinVertical(
			lipgloss.Left,
			chatView,
			inputView,
		)
	}

	mainLayout := lipgloss.JoinHorizontal(
		lipgloss.Top,
		sidebarView,
		rightPanel,
	)

	return mainLayout
}

// helper marshall indent
func jsonMarshalIndent(v interface{}) (string, error) {
	b, err := json.Marshal(v)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func (m *MainModel) handleGhostCommand(args string) {
	if args == "" || args == "help" {
		m.Chat.AppendMessage("system", "Perintah Ghost Agent:\n  /ghost <task>  : spawn background agent baru\n  /ghost list    : lihat daftar agent aktif\n  /ghost show <id>: tampilkan output log agent\n  /ghost kill <id>: matikan agent")
		return
	}

	if args == "list" {
		list := m.GhostMgr.List()
		if len(list) == 0 {
			m.Chat.AppendMessage("system", "Tidak ada background ghost agent yang aktif.")
			return
		}
		var sb strings.Builder
		sb.WriteString("Daftar Ghost Agent Aktif:\n")
		for _, a := range list {
			sb.WriteString(fmt.Sprintf("  #%d [%s] %s (run %.0fs)\n", a.ID, a.Status, a.Task, a.Runtime()))
		}
		m.Chat.AppendMessage("system", sb.String())
		return
	}

	if strings.HasPrefix(args, "show ") {
		idStr := strings.TrimPrefix(args, "show ")
		id, err := strconv.Atoi(idStr)
		if err != nil {
			m.Chat.AppendMessage("system", "ID agent tidak valid.")
			return
		}
		out := m.GhostMgr.GetOutput(id)
		if out == "" {
			m.Chat.AppendMessage("system", fmt.Sprintf("Tidak ada output log untuk Ghost Agent #%d.", id))
		} else {
			if len(out) > 2000 {
				out = out[len(out)-2000:] + "\n... truncated (2000 chars limit)"
			}
			m.Chat.AppendMessage("system", fmt.Sprintf("Log Output Ghost Agent #%d:\n%s", id, out))
		}
		return
	}

	if strings.HasPrefix(args, "kill ") {
		target := strings.TrimPrefix(args, "kill ")
		if target == "all" {
			list := m.GhostMgr.List()
			for _, a := range list {
				m.GhostMgr.Kill(a.ID)
			}
			m.Chat.AppendMessage("system", "Semua background agent dimatikan.")
		} else {
			id, err := strconv.Atoi(target)
			if err != nil {
				m.Chat.AppendMessage("system", "ID agent tidak valid.")
				return
			}
			if m.GhostMgr.Kill(id) {
				m.Chat.AppendMessage("system", fmt.Sprintf("Ghost Agent #%d dimatikan.", id))
			} else {
				m.Chat.AppendMessage("system", fmt.Sprintf("Ghost Agent #%d tidak ditemukan.", id))
			}
		}
		return
	}

	// Default: Spawn task baru
	info, err := m.GhostMgr.Spawn(args)
	if err != nil {
		m.Chat.AppendMessage("system", fmt.Sprintf("Gagal spawn Ghost Agent: %v", err))
	} else {
		m.Chat.AppendMessage("system", fmt.Sprintf("👻 Ghost Agent #%d didelegasikan: %s\nKetik `/ghost list` atau `/ghost show %d` untuk memantau.", info.ID, args, info.ID))
	}
}

func (m MainModel) connectToAgentCmd() tea.Cmd {
	return func() tea.Msg {
		// Jalankan start client
		err := m.IPCClient.Start(m.ProjectRoot, m.ConfigPath, m.InitOpts)
		if err != nil {
			return ErrorMsg{Message: fmt.Sprintf("Gagal menjalankan agen: %v", err)}
		}

		// Ambil status awal
		var statusReply map[string]interface{}
		err = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
		if err != nil {
			return ErrorMsg{Message: fmt.Sprintf("Gagal mengambil status awal agen: %v", err)}
		}

		resumeSession, _ := m.InitOpts["resume_session"].(string)
		if resumeSession != "" {
			var resumeReply map[string]interface{}
			params := map[string]interface{}{"identifier": resumeSession}
			err = m.IPCClient.Call("agent.resume_session", params, &resumeReply)
			if err == nil {
				_ = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
				return StartupResumeMsg{
					Status:        parseStatusReply(statusReply, m.ProjectRoot),
					ResumeMessage: resumeReply["message"].(string),
					RawMessages:   resumeReply["messages"],
				}
			}
		}

		return parseStatusReply(statusReply, m.ProjectRoot)
	}
}

func (m MainModel) fetchModelsCmd() tea.Cmd {
	return func() tea.Msg {
		var reply []ModelSelectorItem
		err := m.IPCClient.Call("agent.list_models", map[string]interface{}{}, &reply)
		if err != nil {
			return ErrorMsg{Message: fmt.Sprintf("Gagal memuat daftar model: %v", err)}
		}
		return ModelsLoadedMsg{Models: reply}
	}
}

func (m MainModel) switchModelCmd(modelID string) tea.Cmd {
	return func() tea.Msg {
		var reply string
		err := m.IPCClient.Call("agent.switch_model", map[string]interface{}{"model_id": modelID}, &reply)
		if err != nil {
			return ErrorMsg{Message: fmt.Sprintf("Gagal mengganti model: %v", err)}
		}

		var statusReply map[string]interface{}
		err = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
		if err != nil {
			return StatusUpdateMsg{
				ModelName:   modelID,
				ProjectName: filepath.Base(m.ProjectRoot),
			}
		}

		return parseStatusReply(statusReply, m.ProjectRoot)
	}
}

func sessionChatMessages(rawMessages []interface{}) []ChatMessage {
	messages := make([]ChatMessage, 0, len(rawMessages))
	for _, raw := range rawMessages {
		message, ok := raw.(map[string]interface{})
		if !ok {
			continue
		}
		role, _ := message["role"].(string)
		content, _ := message["content"].(string)
		if (role == "user" || role == "assistant") && content != "" {
			messages = append(messages, ChatMessage{Role: role, Content: content})
		}
	}
	return messages
}

func parseStatusReply(statusReply map[string]interface{}, projectRoot string) StatusUpdateMsg {
	version, _ := statusReply["version"].(string)
	if version != "" && !strings.HasPrefix(version, "v") {
		version = "v" + version
	}
	if version == "" {
		version = "v0.12.7"
	}
	modelName := "?"
	if value, ok := statusReply["model_name"].(string); ok && value != "" {
		modelName = value
	}
	if value, ok := statusReply["model_id"].(string); ok && value != "" && modelName == "?" {
		modelName = value
	}
	if mStatus, ok := statusReply["model_status"].(map[string]interface{}); ok {
		if active, ok := mStatus["models"].([]interface{}); ok && len(active) > 0 {
			if primary, ok := active[0].(map[string]interface{}); ok {
				modelName, _ = primary["model_id"].(string)
			}
		}
	}

	contextInfo, _ := statusReply["context_info"].(map[string]interface{})
	contextUsed := 0
	contextWindow := 262144
	contextPct := 0.0

	if contextInfo != nil {
		if u, ok := contextInfo["tokens"].(float64); ok {
			contextUsed = int(u)
		}
		if w, ok := contextInfo["window"].(float64); ok {
			contextWindow = int(w)
		}
		if p, ok := contextInfo["pct"].(float64); ok {
			contextPct = p
		}
	}

	projectName := "autokeren"
	if projectRoot != "" {
		projectName = filepath.Base(projectRoot)
	}

	neuronsRemaining := 0
	neuronsQuota := 0
	if sbi, ok := statusReply["status_bar_info"].(map[string]interface{}); ok {
		if nr, ok := sbi["neurons_remaining"].(float64); ok {
			neuronsRemaining = int(nr)
		}
		if nq, ok := sbi["neurons_quota"].(float64); ok {
			neuronsQuota = int(nq)
		}
	}

	var todos []TodoItem
	if rawTodos, ok := statusReply["todos"].([]interface{}); ok {
		for _, rt := range rawTodos {
			if todoMap, ok := rt.(map[string]interface{}); ok {
				content, _ := todoMap["content"].(string)
				status, _ := todoMap["status"].(string)
				todos = append(todos, TodoItem{
					Content: content,
					Status:  status,
				})
			}
		}
	}

	var kanbanTasks []KanbanTask
	if rawKanban, ok := statusReply["kanban_tasks"].([]interface{}); ok {
		for _, rk := range rawKanban {
			if km, ok := rk.(map[string]interface{}); ok {
				idVal, _ := km["id"].(float64)
				title, _ := km["title"].(string)
				desc, _ := km["description"].(string)
				status, _ := km["status"].(string)
				priority, _ := km["priority"].(string)
				created, _ := km["created_at"].(string)
				updated, _ := km["updated_at"].(string)
				kanbanTasks = append(kanbanTasks, KanbanTask{
					ID:          int(idVal),
					Title:       title,
					Description: desc,
					Status:      status,
					Priority:    priority,
					CreatedAt:   created,
					UpdatedAt:   updated,
				})
			}
		}
	}

	sessionID, _ := statusReply["session_id"].(string)
	sessionName, _ := statusReply["session_name"].(string)
	if sessionID == "" {
		sessionID = "default"
	}
	if sessionName == "" {
		sessionName = "default"
	}

	return StatusUpdateMsg{
		ModelName:        modelName,
		ProjectName:      projectName,
		ContextUsed:      contextUsed,
		ContextWindow:    contextWindow,
		ContextPct:       contextPct,
		NeuronsRemaining: neuronsRemaining,
		NeuronsQuota:     neuronsQuota,
		Todos:            todos,
		KanbanTasks:      kanbanTasks,
		Version:          version,
		SessionID:        sessionID,
		SessionName:      sessionName,
	}
}

func (m MainModel) getSelectedTask() (KanbanTask, bool) {
	var colTasks []KanbanTask
	status := "todo"
	if m.SelectedColumn == 1 {
		status = "in_progress"
	} else if m.SelectedColumn == 2 {
		status = "done"
	}

	for _, t := range m.KanbanTasks {
		if t.Status == status {
			colTasks = append(colTasks, t)
		}
	}

	if len(colTasks) == 0 || m.SelectedTaskIndex < 0 || m.SelectedTaskIndex >= len(colTasks) {
		return KanbanTask{}, false
	}
	return colTasks[m.SelectedTaskIndex], true
}

func renderMcpAddDialog(nameInput, cmdInput textinput.Model, activeField int, width int) string {
	dialogStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#10B981")).
		Padding(1, 2).
		Width(width)

	titleStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#10B981")).Bold(true)
	activeLabelStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#10B981")).Bold(true)

	nameLabel := "  Nama Server:      "
	cmdLabel := "  Perintah/Command: "
	if activeField == 0 {
		nameLabel = activeLabelStyle.Render("▸ Nama Server:      ")
	} else {
		cmdLabel = activeLabelStyle.Render("▸ Perintah/Command: ")
	}

	var sb strings.Builder
	sb.WriteString(titleStyle.Render("⚡ TAMBAH MCP SERVER BARU") + "\n\n")
	sb.WriteString(nameLabel + nameInput.View() + "\n")
	sb.WriteString(cmdLabel + cmdInput.View() + "\n\n")
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280")).Render("Tab/Up/Down: Pindah field · Enter: Lanjut/Simpan · Esc: Batal"))

	return dialogStyle.Render(sb.String())
}
