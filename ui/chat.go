package ui

import (
	"strings"

	"github.com/charmbracelet/bubbles/viewport"
	"github.com/charmbracelet/lipgloss"
)

// ChatMessage mewakili entri baris chat
type ChatMessage struct {
	Role    string
	Content string
}

type ChatModel struct {
	Messages []ChatMessage
	Viewport viewport.Model
	Width    int
	Height   int
}

func NewChatModel() ChatModel {
	vp := viewport.New(0, 0)
	vp.Style = lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#2A2A35")).
		Padding(1, 2)

	return ChatModel{
		Viewport: vp,
		Messages: []ChatMessage{},
	}
}

func (m *ChatModel) Resize(width, height int) {
	m.Width = width
	m.Height = height
	m.Viewport.Width = width
	m.Viewport.Height = height - 2 // Sisakan ruang untuk border
}

func (m *ChatModel) AppendMessage(role, content string) {
	// Jika pesan terakhir memiliki role yang sama (misal asinkron chunk), gabungkan
	n := len(m.Messages)
	if n > 0 && m.Messages[n-1].Role == role {
		m.Messages[n-1].Content += content
	} else {
		m.Messages = append(m.Messages, ChatMessage{Role: role, Content: content})
	}
	m.UpdateViewport()
}

func (m *ChatModel) UpdateViewport() {
	var sb strings.Builder
	for _, msg := range m.Messages {
		var header, content string
		
		headerStyle := lipgloss.NewStyle().Bold(true).Padding(0, 1)
		contentStyle := lipgloss.NewStyle().Padding(0, 1)

		switch msg.Role {
		case "user":
			header = headerStyle.Background(lipgloss.Color("#00E5FF")).Foreground(lipgloss.Color("#121214")).Render(" 👤 KAMU ")
			content = contentStyle.Foreground(lipgloss.Color("#E0E0E0")).Render(msg.Content)
		case "assistant":
			header = headerStyle.Background(lipgloss.Color("#34D399")).Foreground(lipgloss.Color("#121214")).Render(" 🤖 AUTOKEREN ")
			content = contentStyle.Foreground(lipgloss.Color("#FFFFFF")).Render(msg.Content)
		case "system":
			header = headerStyle.Background(lipgloss.Color("#FBBF24")).Foreground(lipgloss.Color("#121214")).Render(" ⚙ SYSTEM ")
			content = contentStyle.Foreground(lipgloss.Color("#BDBDBD")).Render(msg.Content)
		case "tool":
			header = headerStyle.Background(lipgloss.Color("#C084FC")).Foreground(lipgloss.Color("#121214")).Render(" 🔧 TOOL ")
			content = contentStyle.Foreground(lipgloss.Color("#A78BFA")).Italic(true).Render(msg.Content)
		}
		
		sb.WriteString(header + "\n" + content + "\n\n")
	}

	m.Viewport.SetContent(sb.String())
	m.Viewport.GotoBottom()
}

func (m ChatModel) View() string {
	return m.Viewport.View()
}
