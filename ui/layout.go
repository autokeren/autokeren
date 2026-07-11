package ui

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/autokeren/autokeren/ghost"
	"github.com/autokeren/autokeren/ipc"
)

// SpinnerTickMsg adalah tick untuk animasi spinner
type SpinnerTickMsg struct{}

// Definisikan tipe-tipe pesan Bubble Tea untuk komunikasi asinkron dari daemon
type ChunkMsg struct{ Text string }
type ModelStartMsg struct{}
type ModelEndMsg struct {
	Content string
	ModelID string
	Usage   map[string]interface{}
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
type ErrorMsg struct{ Message string }
type ModelsLoadedMsg struct {
	Models []ModelSelectorItem
}
type StatusUpdateMsg struct {
	ModelName        string
	ProjectName      string
	ContextUsed      int
	ContextWindow    int
	ContextPct       float64
	NeuronsRemaining int
	NeuronsQuota     int
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
	{Name: "/model", Description: "Ganti model AI yang digunakan"},
	{Name: "/ghost", Description: "Kelola background agent"},
	{Name: "/compact", Description: "Kompak/ringkas konteks percakapan"},
	{Name: "/reset", Description: "Reset sesi percakapan baru"},
	{Name: "/q", Description: "Keluar dari autokeren"},
}

type MainModel struct {
	Chat              ChatModel
	Sidebar           SidebarModel
	TextInput         textinput.Model
	IPCClient         *ipc.Client
	GhostMgr          *ghost.GhostManager
	ProjectRoot       string
	ConfigPath        string
	InitOpts          map[string]interface{}

	Width  int
	Height int

	AgentRunning      bool
	PermissionReq     *PermissionConfirmReq
	ActiveModelID     string

	Initialized       bool
	InitError         string
	ActiveEditingFile string

	ShowModelSelector  bool
	SelectorModels     []ModelSelectorItem
	SelectedModelIndex int

	ShowAutocomplete  bool
	FilteredCmds      []SlashCommandInfo
	SelectedCommand   int

	// Spinner state
	SpinnerFrame int
	SpinnerDir   int // 1 = kanan, -1 = kiri (untuk bouncing ball)
	SpinnerPos   int // posisi bola saat ini

	// Always-allow set: tool name yang sudah diizinkan selama sesi
	AlwaysAllow map[string]bool

	// Task aktif saat ini (ditampilkan di sidebar)
	CurrentTask string
}

func NewMainModel(client *ipc.Client, ghostMgr *ghost.GhostManager, projectRoot, configPath string, opts map[string]interface{}) MainModel {
	ti := textinput.New()
	ti.Placeholder = "Ketik perintah atau / untuk melihat menu..."
	ti.Focus()
	ti.CharLimit = 1000
	ti.Width = 80
	ti.Prompt = " ❯ "
	ti.PromptStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#00E5FF")).Bold(true)

	return MainModel{
		Chat:               NewChatModel(),
		Sidebar:            NewSidebarModel(),
		TextInput:          ti,
		IPCClient:          client,
		GhostMgr:           ghostMgr,
		ProjectRoot:        projectRoot,
		ConfigPath:         configPath,
		InitOpts:           opts,
		ActiveEditingFile:  "",
		ShowModelSelector:  false,
		SelectorModels:     []ModelSelectorItem{},
		SelectedModelIndex: 0,
		ShowAutocomplete:   false,
		FilteredCmds:       []SlashCommandInfo{},
		SelectedCommand:    0,
		SpinnerFrame:       0,
		SpinnerDir:         1,
		SpinnerPos:         0,
		AlwaysAllow:        make(map[string]bool),
		CurrentTask:        "",
	}
}

func (m MainModel) Init() tea.Cmd {
	return tea.Batch(
		textinput.Blink,
		m.connectToAgentCmd(),
		spinnerTick(),
	)
}

func spinnerTick() tea.Cmd {
	return tea.Tick(120*time.Millisecond, func(_ time.Time) tea.Msg {
		return SpinnerTickMsg{}
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
		m.AgentRunning = false
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
		m.Chat.AppendMessage("system", fmt.Sprintf("retry #%d (%.0fs) %s", msg.Attempt, msg.Delay, msg.Message))

	case ErrorMsg:
		m.InitError = msg.Message
		m.Chat.AppendMessage("system", fmt.Sprintf("error: %s", msg.Message))
		
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

	case PermissionConfirmReq:
		m.PermissionReq = &msg
		m.Chat.AppendMessage("system", fmt.Sprintf("permission required: %s — %s", msg.Name, msg.Description))

	case tea.KeyMsg:
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
					go func() {
						var reply map[string]interface{}
						err := m.IPCClient.Call("agent.compact", map[string]interface{}{}, &reply)
						if err == nil {
							msg2, _ := reply["message"].(string)
							m.Chat.AppendMessage("system", msg2)
						} else {
							m.Chat.AppendMessage("system", fmt.Sprintf("Gagal compact: %v", err))
						}
					}()
					return m, nil
				}
				if selected.Name == "/reset" {
					m.TextInput.SetValue("")
					m.AgentRunning = true
					m.Chat.AppendMessage("system", "Mereset sesi percakapan...")
					go func() {
						var reply string
						err := m.IPCClient.Call("agent.reset", map[string]interface{}{}, &reply)
						if err == nil {
							m.Chat.Messages = []ChatMessage{}
							m.Chat.AppendMessage("system", "Sesi berhasil direset.")
						} else {
							m.Chat.AppendMessage("system", fmt.Sprintf("Gagal reset: %v", err))
						}
					}()
					return m, nil
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
				// Allow sekali ini
				m.PermissionReq.RespChan <- true
				m.Chat.AppendMessage("system", fmt.Sprintf("allowed: %s", m.PermissionReq.Name))
				m.PermissionReq = nil
			case "a", "A":
				// Allow selalu selama sesi ini
				m.AlwaysAllow[m.PermissionReq.Name] = true
				m.PermissionReq.RespChan <- true
				m.Chat.AppendMessage("system", fmt.Sprintf("always allowed (session): %s", m.PermissionReq.Name))
				m.PermissionReq = nil
			case "n", "N", "esc":
				// Tolak sekali ini
				m.PermissionReq.RespChan <- false
				m.Chat.AppendMessage("system", fmt.Sprintf("denied: %s", m.PermissionReq.Name))
				m.PermissionReq = nil
			case "q", "Q":
				// Abort: tolak dan hentikan agent
				m.PermissionReq.RespChan <- false
				m.PermissionReq = nil
				m.AgentRunning = false
				m.Chat.AppendMessage("system", "task aborted.")
			}
			return m, nil
		}

		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyCtrlQ:
			m.IPCClient.Close()
			return m, tea.Quit
			
		case tea.KeyEnter:
			val := m.TextInput.Value()
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
			
			if val == "/compact" {
				m.AgentRunning = true
				m.Chat.AppendMessage("system", "Mengompak context...")
				go func() {
					var reply map[string]interface{}
					err := m.IPCClient.Call("agent.compact", map[string]interface{}{}, &reply)
					if err == nil {
						msg, _ := reply["message"].(string)
						m.Chat.AppendMessage("system", msg)
					} else {
						m.Chat.AppendMessage("system", fmt.Sprintf("Gagal compact: %v", err))
					}
				}()
				return m, nil
			}
			
			if val == "/reset" {
				m.AgentRunning = true
				m.Chat.AppendMessage("system", "Mereset sesi percakapan...")
				go func() {
					var reply string
					err := m.IPCClient.Call("agent.reset", map[string]interface{}{}, &reply)
					if err == nil {
						m.Chat.AppendMessage("system", "Sesi berhasil direset.")
						m.Chat.Messages = []ChatMessage{}
					} else {
						m.Chat.AppendMessage("system", fmt.Sprintf("Gagal reset: %v", err))
					}
				}()
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
			go func(userInput string) {
				runParams := map[string]interface{}{
					"user_input": userInput,
				}
				var reply map[string]interface{}
				err := m.IPCClient.Call("agent.run", runParams, &reply)
				if err != nil {
					m.IPCClient.Close()
				}
			}(val)
			
			return m, nil
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

		chatView := chatStyle.Render("⚙ Menghubungkan ke agen Python di latar belakang...\nHarap tunggu sebentar...")

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

	chatView := m.Chat.View()
	sidebarView := m.Sidebar.View()

	panelWidth := m.Width - m.Sidebar.Width - 4

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

	// Permission dialog 4-opsi overlay
	var permissionView string
	if m.PermissionReq != nil {
		permStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#FBBF24")).
			Padding(1, 2).
			Width(panelWidth)

		titleStyle  := lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)
		toolStyle   := lipgloss.NewStyle().Foreground(lipgloss.Color("#F8FAFC")).Bold(true)
		descStyle   := lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280")).Italic(true)
		divStyle    := lipgloss.NewStyle().Foreground(lipgloss.Color("#374151"))

		keyStyle    := lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)
		labelOkStyle:= lipgloss.NewStyle().Foreground(lipgloss.Color("#34D399"))
		labelAlStyle:= lipgloss.NewStyle().Foreground(lipgloss.Color("#38BDF8"))
		labelNoStyle:= lipgloss.NewStyle().Foreground(lipgloss.Color("#F87171"))
		labelAbStyle:= lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280"))

		var pb strings.Builder
		pb.WriteString(titleStyle.Render("  permission required") + "\n")
		pb.WriteString(divStyle.Render(strings.Repeat("─", panelWidth-8)) + "\n")
		pb.WriteString(toolStyle.Render("  "+m.PermissionReq.Name) + "\n")
		if m.PermissionReq.Description != "" {
			pb.WriteString(descStyle.Render("  "+m.PermissionReq.Description) + "\n")
		}
		pb.WriteString("\n")
		pb.WriteString(
			keyStyle.Render("  [y]") + labelOkStyle.Render(" allow once") + "   " +
			keyStyle.Render("[a]") + labelAlStyle.Render(" always (session)") + "   " +
			keyStyle.Render("[n]") + labelNoStyle.Render(" deny") + "   " +
			keyStyle.Render("[q]") + labelAbStyle.Render(" abort task"),
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
		for i, item := range m.SelectorModels {
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
		msSb.WriteString("\n" + lipgloss.NewStyle().Foreground(lipgloss.Color("#888899")).Render("  ↑↓/Tab navigasi · Enter pilih · Esc batal · 1-9 pilih cepat"))
		modelSelectorView = msStyle.Render(msSb.String())
	}

	var rightPanel string
	switch {
	case m.ShowModelSelector:
		rightPanel = lipgloss.JoinVertical(
			lipgloss.Left,
			chatView,
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
			return ErrorMsg{Message: fmt.Sprintf("Gagal menjalankan daemon Python: %v", err)}
		}

		// Ambil status awal
		var statusReply map[string]interface{}
		err = m.IPCClient.Call("agent.status", map[string]interface{}{}, &statusReply)
		if err != nil {
			return ErrorMsg{Message: fmt.Sprintf("Gagal mengambil status awal agen: %v", err)}
		}

		// Parse status awal
		modelName := "?"
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

		// Ambil base name dari project root secara aman
		projectName := "autokeren"
		if m.ProjectRoot != "" {
			projectName = filepath.Base(m.ProjectRoot)
		}

		return StatusUpdateMsg{
			ModelName:     modelName,
			ProjectName:   projectName,
			ContextUsed:   contextUsed,
			ContextWindow: contextWindow,
			ContextPct:   contextPct,
		}
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

		projectName := filepath.Base(m.ProjectRoot)
		contextUsed := 0
		contextWindow := 262144
		contextPct := 0.0
		
		contextInfo, _ := statusReply["context_info"].(map[string]interface{})
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

		return StatusUpdateMsg{
			ModelName:     modelID,
			ProjectName:   projectName,
			ContextUsed:   contextUsed,
			ContextWindow: contextWindow,
			ContextPct:    contextPct,
		}
	}
}
