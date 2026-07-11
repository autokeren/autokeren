package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

type SidebarModel struct {
	ModelName        string
	ProjectName      string
	ContextUsed      int
	ContextWindow    int
	ContextPct       float64
	NeuronsRemaining int
	NeuronsQuota     int
	Width            int
	Height           int
}

func NewSidebarModel() SidebarModel {
	return SidebarModel{
		ModelName:     "?",
		ProjectName:   "?",
		ContextWindow: 262144,
	}
}

func (m SidebarModel) View() string {
	style := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#81C784")).
		Padding(1, 1).
		Width(m.Width - 4).
		Height(m.Height - 2)

	var sb strings.Builder

	// Title Banner
	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#FF5252")).
		Align(lipgloss.Center).
		Width(m.Width - 6)
	sb.WriteString(titleStyle.Render("⚡ AUTOKEREN ⚡") + "\n\n")

	// Info Project
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#E0E0E0")).Render("📂 Project:") + "\n")
	sb.WriteString(lipgloss.NewStyle().Bold(true).Render(m.ProjectName) + "\n\n")

	// Info Model
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#E0E0E0")).Render("🤖 Model:") + "\n")
	sb.WriteString(lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#4FC3F7")).Render(m.ModelName) + "\n\n")

	// Context Bar
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#E0E0E0")).Render("📊 Context Window:") + "\n")
	sb.WriteString(fmt.Sprintf("%d/%d tokens (%.1f%%)\n", m.ContextUsed, m.ContextWindow, m.ContextPct))
	
	barWidth := m.Width - 8
	if barWidth > 5 {
		filled := int(float64(barWidth) * m.ContextPct / 100.0)
		if filled < 0 {
			filled = 0
		}
		if filled > barWidth {
			filled = barWidth
		}
		unfilled := barWidth - filled
		
		barStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#81C784"))
		bgStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#424242"))
		sb.WriteString(barStyle.Render(strings.Repeat("█", filled)) + bgStyle.Render(strings.Repeat("░", unfilled)) + "\n\n")
	}

	// Neurons Quota jika ada
	if m.NeuronsQuota > 0 {
		sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#E0E0E0")).Render("🧠 Neurons Quota:") + "\n")
		sb.WriteString(fmt.Sprintf("%d/%d used\n\n", m.NeuronsQuota-m.NeuronsRemaining, m.NeuronsQuota))
	}

	// Short Help / Shortcuts
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#9E9E9E")).Render("Pintasan:") + "\n")
	sb.WriteString("  [ctrl+c] Keluar\n")
	sb.WriteString("  [ctrl+q] Keluar TUI\n")
	sb.WriteString("  [/model] Ganti Model\n")
	sb.WriteString("  [/compact] Ringkas Chat\n")

	return style.Render(sb.String())
}
