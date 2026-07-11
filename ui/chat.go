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
		BorderForeground(lipgloss.Color("#4FC3F7")).
		Padding(0, 1)

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
		roleStyle := lipgloss.NewStyle().Bold(true)
		contentStyle := lipgloss.NewStyle()

		switch msg.Role {
		case "user":
			roleStyle = roleStyle.Foreground(lipgloss.Color("#4FC3F7"))
			sb.WriteString(roleStyle.Render("kamu> ") + contentStyle.Render(msg.Content) + "\n\n")
		case "assistant":
			roleStyle = roleStyle.Foreground(lipgloss.Color("#81C784"))
			sb.WriteString(roleStyle.Render("autokeren> ") + contentStyle.Render(msg.Content) + "\n\n")
		case "system":
			roleStyle = roleStyle.Foreground(lipgloss.Color("#FFB74D"))
			sb.WriteString(roleStyle.Render("sistem> ") + contentStyle.Render(msg.Content) + "\n\n")
		case "tool":
			roleStyle = roleStyle.Foreground(lipgloss.Color("#9575CD"))
			sb.WriteString(roleStyle.Render("tool> ") + contentStyle.Render(msg.Content) + "\n\n")
		}
	}

	m.Viewport.SetContent(sb.String())
	m.Viewport.GotoBottom()
}

func (m ChatModel) View() string {
	return m.Viewport.View()
}
