package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

func (m MainModel) DebateView(panelWidth int, panelHeight int) string {
	list := m.GhostMgr.List()

	leftWidth := 32
	if leftWidth > panelWidth/3 {
		leftWidth = panelWidth / 3
	}
	rightWidth := panelWidth - leftWidth - 2

	leftStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#2D3748")).
		Padding(1, 1).
		Width(leftWidth).
		Height(panelHeight - 6)

	var leftSb strings.Builder
	titleStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#A78BFA")).Bold(true)
	leftSb.WriteString(titleStyle.Render("🤖 ACTIVE AGENTS") + "\n\n")

	if len(list) == 0 {
		leftSb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#4B5563")).Italic(true).Render("Tidak ada agent aktif.\nKetik /ghost <task> untuk memulai."))
	} else {
		for _, a := range list {
			selectedMarker := "  "
			isSel := a.ID == m.SelectedDebateAgentID
			if isSel {
				selectedMarker = "▸ "
			}

			statusStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#94A3B8"))
			if a.Status == "running" {
				statusStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)
			} else if a.Status == "completed" {
				statusStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#34D399"))
			} else if a.Status == "failed" {
				statusStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#F87171"))
			}

			shortTask := a.Task
			if len([]rune(shortTask)) > leftWidth-6 {
				shortTask = string([]rune(shortTask)[:leftWidth-9]) + "..."
			}

			itemStyle := lipgloss.NewStyle()
			if isSel {
				itemStyle = itemStyle.Foreground(lipgloss.Color("#FFFFFF")).Background(lipgloss.Color("#5B21B6")).Bold(true)
			} else {
				itemStyle = itemStyle.Foreground(lipgloss.Color("#DDD6FE"))
			}

			leftSb.WriteString(fmt.Sprintf("%s%s\n   %s · %.0fs\n\n",
				selectedMarker,
				itemStyle.Render(fmt.Sprintf("#%d: %s", a.ID, shortTask)),
				statusStyle.Render(strings.ToUpper(a.Status)),
				a.Runtime(),
			))
		}
	}
	leftPanel := leftStyle.Render(leftSb.String())

	rightStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#5B21B6")).
		Padding(1, 2).
		Width(rightWidth).
		Height(panelHeight - 6)

	var rightContent string
	if m.SelectedDebateAgentID == 0 {
		rightContent = lipgloss.NewStyle().Foreground(lipgloss.Color("#4B5563")).Italic(true).Render("Pilih salah satu agent di panel kiri untuk melihat log aktivitas perdebatan secara real-time.")
	} else {
		logText := m.GhostMgr.GetOutput(m.SelectedDebateAgentID)
		if logText == "" {
			rightContent = lipgloss.NewStyle().Foreground(lipgloss.Color("#4B5563")).Italic(true).Render("Menunggu output log...")
		} else {
			lines := strings.Split(logText, "\n")
			maxLines := panelHeight - 10
			if len(lines) > maxLines {
				lines = lines[len(lines)-maxLines:]
			}
			rightContent = strings.Join(lines, "\n")
		}
	}

	rightTitleStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)
	rightPanelContent := rightTitleStyle.Render(fmt.Sprintf("💬 LOG DISKUSI AGENT #%d", m.SelectedDebateAgentID)) + "\n\n" + rightContent
	rightPanel := rightStyle.Render(rightPanelContent)

	body := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, rightPanel)

	footerStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6B7280")).
		Italic(true).
		PaddingTop(1)

	footer := footerStyle.Render(
		"  ←/→: Pilih Agent  ·  k: Kill Agent  ·  Tab/Ctrl+D: Kembali ke Chat",
	)

	return lipgloss.JoinVertical(lipgloss.Left, body, footer)
}
