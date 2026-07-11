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
		BorderForeground(lipgloss.Color("#2A2A35")).
		Padding(1, 2).
		Width(m.Width - 4).
		Height(m.Height - 2)

	var sb strings.Builder

	// Title Banner
	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#00E5FF")).
		Align(lipgloss.Center).
		Width(m.Width - 8)
	sb.WriteString(titleStyle.Render("⚡ AUTOKEREN ⚡") + "\n\n")

	// Info Project
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#888899")).Render("󰉋  PROJECT:") + "\n")
	sb.WriteString(lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#E0E0E0")).Render(m.ProjectName) + "\n\n")

	// Info Model
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#888899")).Render("🤖 ACTIVE MODEL:") + "\n")
	sb.WriteString(lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#00E5FF")).Render(m.ModelName) + "\n\n")

	// Context Bar
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#888899")).Render("📊 CONTEXT MEMORY:") + "\n")
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#E0E0E0")).Render(fmt.Sprintf("%d/%d tokens (%.1f%%)", m.ContextUsed, m.ContextWindow, m.ContextPct)) + "\n")
	
	barWidth := m.Width - 10
	if barWidth > 5 {
		filled := int(float64(barWidth) * m.ContextPct / 100.0)
		if filled < 0 {
			filled = 0
		}
		if filled > barWidth {
			filled = barWidth
		}
		unfilled := barWidth - filled
		
		// Tentukan warna progress bar berdasarkan persentase
		barColor := "#34D399" // Hijau jika < 70%
		if m.ContextPct >= 90.0 {
			barColor = "#FF5252" // Merah jika > 90%
		} else if m.ContextPct >= 70.0 {
			barColor = "#FBBF24" // Kuning jika > 70%
		}
		
		barStyle := lipgloss.NewStyle().Foreground(lipgloss.Color(barColor))
		bgStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#2A2A35"))
		sb.WriteString(barStyle.Render(strings.Repeat("█", filled)) + bgStyle.Render(strings.Repeat("░", unfilled)) + "\n\n")
	}

	// Neurons Quota jika ada
	if m.NeuronsQuota > 0 {
		sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#888899")).Render("🧠 NEURON QUOTA:") + "\n")
		sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#E0E0E0")).Render(fmt.Sprintf("%d/%d used", m.NeuronsQuota-m.NeuronsRemaining, m.NeuronsQuota)) + "\n\n")
	}

	// Short Help / Shortcuts
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#666677")).Render("PINTASAN KEYBOARD:") + "\n")
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#A0A0B0")).Render(
		"  ^C      Keluar TUI\n" +
		"  /model  Ganti Model\n" +
		"  /ghost  Background Agent\n" +
		"  /compact Ringkas Chat\n" +
		"  /reset  Mulai Ulang Sesi\n",
	))

	return style.Render(sb.String())
}
