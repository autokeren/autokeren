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
		BorderForeground(lipgloss.Color("#1E1E2A")).
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
	m.Viewport.Height = height - 2
}

func (m *ChatModel) AppendMessage(role, content string) {
	n := len(m.Messages)
	if n > 0 && m.Messages[n-1].Role == role && role != "system" {
		if role == "tool" {
			// Pastikan ada newline pemisah antar log tool agar tidak menyatu dalam satu baris
			if !strings.HasSuffix(m.Messages[n-1].Content, "\n") {
				m.Messages[n-1].Content += "\n"
			}
		}
		m.Messages[n-1].Content += content
	} else {
		m.Messages = append(m.Messages, ChatMessage{Role: role, Content: content})
	}
	m.UpdateViewport()
}

// renderToolLine renders satu baris tool activity secara compact & profesional
func renderToolLine(content string) string {
	lines := strings.Split(strings.TrimSpace(content), "\n")
	if len(lines) == 0 {
		return ""
	}

	var sb strings.Builder
	dimStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#4B5563"))
	labelStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280"))
	pathStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#9CA3AF")).Italic(true)
	okStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#34D399")).Bold(true)
	errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#F87171")).Bold(true)
	infoStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#60A5FA"))
	pipeStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#374151"))

	for i, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		prefix := dimStyle.Render("  │ ")
		if i == 0 {
			prefix = dimStyle.Render("  ├ ")
		}

		// Deteksi tipe baris dan render sesuai konteks
		switch {
		case strings.HasPrefix(trimmed, "✓"):
			rest := strings.TrimPrefix(trimmed, "✓")
			sb.WriteString(prefix + okStyle.Render("✓") + labelStyle.Render(rest) + "\n")
		case strings.HasPrefix(trimmed, "✗"):
			rest := strings.TrimPrefix(trimmed, "✗")
			sb.WriteString(prefix + errStyle.Render("✗") + labelStyle.Render(rest) + "\n")
		case strings.HasPrefix(trimmed, "📂 Path:"):
			path := strings.TrimPrefix(trimmed, "📂 Path:")
			sb.WriteString(pipeStyle.Render("     ") + pathStyle.Render(strings.TrimSpace(path)) + "\n")
		case strings.HasPrefix(trimmed, "⚙ Status:"):
			status := strings.TrimPrefix(trimmed, "⚙ Status:")
			sb.WriteString(prefix + labelStyle.Render("→ ") + infoStyle.Render(strings.TrimSpace(status)) + "\n")
		case strings.HasPrefix(trimmed, "⚠ Error:"):
			errMsg := strings.TrimPrefix(trimmed, "⚠ Error:")
			sb.WriteString(prefix + errStyle.Render("! ") + labelStyle.Render(strings.TrimSpace(errMsg)) + "\n")
		case strings.HasPrefix(trimmed, "│"):
			rest := strings.TrimPrefix(trimmed, "│")
			sb.WriteString(dimStyle.Render("     ╎ ") + labelStyle.Render(strings.TrimSpace(rest)) + "\n")
		case strings.HasPrefix(trimmed, "📝"):
			rest := strings.TrimPrefix(trimmed, "📝")
			sb.WriteString(prefix + infoStyle.Render("◆ ") + labelStyle.Render(strings.TrimSpace(rest)) + "\n")
		case strings.HasPrefix(trimmed, "⏺"):
			rest := strings.TrimPrefix(trimmed, "⏺")
			sb.WriteString(prefix + infoStyle.Render("◈ ") + labelStyle.Render(strings.TrimSpace(rest)) + "\n")
		default:
			sb.WriteString(prefix + labelStyle.Render(trimmed) + "\n")
		}
	}
	return sb.String()
}

func (m *ChatModel) UpdateViewport() {
	var sb strings.Builder

	// Styles
	userPrefixStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#38BDF8")).
		Bold(true)
	userTextStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#E2E8F0")).
		PaddingLeft(4)

	asstPrefixStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#34D399")).
		Bold(true)
	asstTextStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#F8FAFC")).
		PaddingLeft(4)

	sysPrefixStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6B7280"))
	sysTextStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6B7280")).
		PaddingLeft(4).
		Italic(true)

	dividerStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#1E1E2A"))

	for i, msg := range m.Messages {
		// Separator tipis antar blok (kecuali tool—inline aja)
		if i > 0 && msg.Role != "tool" && m.Messages[i-1].Role != "tool" {
			sb.WriteString(dividerStyle.Render(strings.Repeat("─", 2)) + "\n")
		}

		switch msg.Role {
		case "user":
			sb.WriteString(userPrefixStyle.Render("❯ ") + userPrefixStyle.Foreground(lipgloss.Color("#94A3B8")).Render("you") + "\n")
			sb.WriteString(userTextStyle.Render(msg.Content) + "\n")

		case "assistant":
			sb.WriteString(asstPrefixStyle.Render("◆ ") + asstPrefixStyle.Foreground(lipgloss.Color("#6EE7B7")).Render("autokeren") + "\n")
			sb.WriteString(asstTextStyle.Render(msg.Content) + "\n")

		case "system":
			text := strings.TrimSpace(msg.Content)
			sb.WriteString(sysPrefixStyle.Render("  · ") + sysTextStyle.PaddingLeft(0).Render(text) + "\n")

		case "tool":
			sb.WriteString(renderToolLine(msg.Content))
		}
	}

	m.Viewport.SetContent(sb.String())
	m.Viewport.GotoBottom()
}

func (m ChatModel) View() string {
	return m.Viewport.View()
}
