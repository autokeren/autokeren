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
		ModelName:     "—",
		ProjectName:   "—",
		ContextWindow: 262144,
	}
}

func (m SidebarModel) View() string {
	w := m.Width - 4
	if w < 4 {
		w = 4
	}

	outerStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#1E1E2A")).
		Padding(1, 2).
		Width(w).
		Height(m.Height - 2)

	// ── Styles ──
	brandStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#38BDF8")).
		Width(w - 4).
		Align(lipgloss.Center)

	sectionLabelStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#374151"))

	valueStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#CBD5E1")).
		Bold(true)

	dimStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#4B5563"))

	accentStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#38BDF8"))

	hintStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#374151"))

	dividerStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#1E1E2A"))

	divider := dividerStyle.Render(strings.Repeat("─", w-4))

	var sb strings.Builder

	// Brand
	sb.WriteString(brandStyle.Render("autokeren") + "\n")
	sb.WriteString(divider + "\n\n")

	// Project
	sb.WriteString(sectionLabelStyle.Render("project") + "\n")
	sb.WriteString(valueStyle.Render(truncate(m.ProjectName, w-4)) + "\n\n")

	// Model
	sb.WriteString(sectionLabelStyle.Render("model") + "\n")
	modelDisplay := m.ModelName
	// Potong prefix panjang model ID supaya muat
	if idx := strings.LastIndex(modelDisplay, "/"); idx >= 0 {
		modelDisplay = modelDisplay[idx+1:]
	}
	sb.WriteString(accentStyle.Render(truncate(modelDisplay, w-4)) + "\n\n")

	// Context
	sb.WriteString(sectionLabelStyle.Render("context") + "\n")
	if m.ContextUsed > 0 {
		sb.WriteString(dimStyle.Render(fmt.Sprintf("%s / %s  %.1f%%",
			humanTokens(m.ContextUsed),
			humanTokens(m.ContextWindow),
			m.ContextPct,
		)) + "\n")
	} else {
		sb.WriteString(dimStyle.Render("—") + "\n")
	}

	barW := w - 4
	if barW > 3 && m.ContextWindow > 0 {
		filled := int(float64(barW) * m.ContextPct / 100.0)
		if filled < 0 {
			filled = 0
		}
		if filled > barW {
			filled = barW
		}
		unfilled := barW - filled

		barColor := "#34D399"
		if m.ContextPct >= 90.0 {
			barColor = "#F87171"
		} else if m.ContextPct >= 70.0 {
			barColor = "#FBBF24"
		}

		barStyle := lipgloss.NewStyle().Foreground(lipgloss.Color(barColor))
		bgBarStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#1E2433"))
		sb.WriteString(barStyle.Render(strings.Repeat("▪", filled)) +
			bgBarStyle.Render(strings.Repeat("▪", unfilled)) + "\n\n")
	} else {
		sb.WriteString("\n")
	}

	// Neurons
	if m.NeuronsQuota > 0 {
		sb.WriteString(sectionLabelStyle.Render("quota") + "\n")
		used := m.NeuronsQuota - m.NeuronsRemaining
		pct := 0.0
		if m.NeuronsQuota > 0 {
			pct = float64(used) / float64(m.NeuronsQuota) * 100.0
		}
		sb.WriteString(dimStyle.Render(fmt.Sprintf("%d / %d  %.0f%%", used, m.NeuronsQuota, pct)) + "\n\n")
	}

	sb.WriteString(divider + "\n\n")

	// Shortcuts
	sb.WriteString(hintStyle.Render("shortcuts") + "\n")
	shortcuts := []struct{ key, desc string }{
		{"/", "slash commands"},
		{"↑↓", "navigasi menu"},
		{"^c", "keluar"},
	}
	for _, s := range shortcuts {
		sb.WriteString(
			dimStyle.Render("  ")+
				accentStyle.Render(fmt.Sprintf("%-5s", s.key))+
				hintStyle.Render(s.desc)+"\n",
		)
	}

	return outerStyle.Render(sb.String())
}

func truncate(s string, max int) string {
	if max <= 3 {
		return s
	}
	runes := []rune(s)
	if len(runes) <= max {
		return s
	}
	return string(runes[:max-1]) + "…"
}

func humanTokens(n int) string {
	if n >= 1000 {
		return fmt.Sprintf("%.1fk", float64(n)/1000.0)
	}
	return fmt.Sprintf("%d", n)
}
