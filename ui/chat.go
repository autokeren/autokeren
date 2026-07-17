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
	m.UpdateViewportScroll(role == "user")
}

// renderToolLine renders satu baris tool activity secara compact & profesional dengan line wrapping
func renderToolLine(content string, textWidth int) string {
	lines := strings.Split(strings.TrimSpace(content), "\n")
	if len(lines) == 0 {
		return ""
	}

	var sb strings.Builder
	dimStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#4B5563"))

	// Tool width offset: kurangi 6 kolom untuk prefix indent
	toolWidth := textWidth - 6
	if toolWidth < 10 {
		toolWidth = 10
	}

	labelStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280")).Width(toolWidth)
	pathStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#9CA3AF")).Italic(true).Width(toolWidth)
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

func renderAssistantText(content string, textWidth int) string {
	lines := strings.Split(content, "\n")
	var sb strings.Builder
	inCode := false
	for _, raw := range lines {
		line := strings.TrimRight(raw, " \t")
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "```") {
			inCode = !inCode
			continue
		}
		if inCode {
			codeStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#67E8F9")).Width(textWidth)
			sb.WriteString(codeStyle.Render(line) + "\n")
			continue
		}
		if strings.HasPrefix(trimmed, "#") {
			heading := strings.TrimSpace(strings.TrimLeft(trimmed, "#"))
			headingStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#67E8F9")).Bold(true).Width(textWidth)
			sb.WriteString(headingStyle.Render(heading) + "\n")
			continue
		}
		if strings.HasPrefix(trimmed, "|---") || strings.HasPrefix(trimmed, "| ---") {
			dimStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#475569")).Width(textWidth)
			sb.WriteString(dimStyle.Render(trimmed) + "\n")
			continue
		}
		sb.WriteString(renderAssistantInline(line, textWidth) + "\n")
	}
	return strings.TrimSuffix(sb.String(), "\n")
}

func renderAssistantInline(line string, textWidth int) string {
	baseStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#F8FAFC")).PaddingLeft(4).Width(textWidth)
	boldStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FFFFFF")).Bold(true)
	codeStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#67E8F9"))
	var out strings.Builder
	for len(line) > 0 {
		if strings.HasPrefix(line, "**") {
			end := strings.Index(line[2:], "**")
			if end >= 0 {
				out.WriteString(boldStyle.Render(line[2 : end+2]))
				line = line[end+4:]
				continue
			}
		}
		if strings.HasPrefix(line, "`") {
			end := strings.Index(line[1:], "`")
			if end >= 0 {
				out.WriteString(codeStyle.Render(line[1 : end+1]))
				line = line[end+2:]
				continue
			}
		}
		out.WriteByte(line[0])
		line = line[1:]
	}
	return baseStyle.Render(out.String())
}

func (m *ChatModel) UpdateViewport() {
	m.UpdateViewportScroll(false)
}

func (m *ChatModel) UpdateViewportScroll(force bool) {
	var sb strings.Builder

	// Guard: Bubble Tea viewport crashes on SetContent/GotoBottom with
	// non-positive dimensions (e.g. before the terminal size is known).
	if m.Viewport.Width <= 0 || m.Viewport.Height <= 0 {
		if m.Width > 0 && m.Height > 0 {
			m.Resize(m.Width, m.Height)
		} else {
			return
		}
	}

	// Hitung sisa lebar untuk text setelah dikurangi padding dan border (8 kolom)
	textWidth := m.Viewport.Width - 8
	if textWidth < 10 {
		textWidth = 10
	}

	// Styles
	userPrefixStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#38BDF8")).
		Bold(true)
	userTextStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#E2E8F0")).
		PaddingLeft(4).
		Width(textWidth)

	asstPrefixStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#34D399")).
		Bold(true)
	sysPrefixStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6B7280"))
	sysTextStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6B7280")).
		Italic(true).
		Width(textWidth + 4) // system prefix tidak pakai padding, jadi lebar penuh

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
			sb.WriteString(renderAssistantText(msg.Content, textWidth) + "\n")

		case "system":
			text := strings.TrimSpace(msg.Content)
			sb.WriteString(sysPrefixStyle.Render("  · ") + sysTextStyle.Render(text) + "\n")

		case "tool":
			sb.WriteString(renderToolLine(msg.Content, textWidth))
		}
	}

	wasAtBottom := m.Viewport.AtBottom()
	m.Viewport.SetContent(sb.String())
	if force || wasAtBottom {
		m.Viewport.GotoBottom()
	}
}

func (m ChatModel) View() string {
	return m.Viewport.View()
}
