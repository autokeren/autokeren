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
	CurrentTask      string
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

	barInnerW := w - 4
	if barInnerW < 3 {
		barInnerW = 3
	}

	// ── Styles ──
	brandStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#38BDF8")).
		Width(w - 4).
		Align(lipgloss.Center)

	labelStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#374151"))

	valueStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#CBD5E1")).
		Bold(true)

	dimStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#4B5563"))

	accentStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#38BDF8"))

	warnStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#FBBF24"))

	errStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#F87171"))

	okStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#34D399"))

	taskStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#A78BFA")).
		Italic(true)

	dividerStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#1E2433"))

	divider := dividerStyle.Render(strings.Repeat("─", w-4))

	var sb strings.Builder

	// Brand
	sb.WriteString(brandStyle.Render("autokeren") + "\n")
	sb.WriteString(divider + "\n\n")

	// Project
	sb.WriteString(labelStyle.Render("project") + "\n")
	sb.WriteString(valueStyle.Render(truncate(m.ProjectName, w-4)) + "\n\n")

	// Model
	sb.WriteString(labelStyle.Render("model") + "\n")
	modelDisplay := m.ModelName
	if idx := strings.LastIndex(modelDisplay, "/"); idx >= 0 {
		modelDisplay = modelDisplay[idx+1:]
	}
	sb.WriteString(accentStyle.Render(truncate(modelDisplay, w-4)) + "\n\n")

	// ── Context ──
	sb.WriteString(labelStyle.Render("context") + "\n")
	if m.ContextUsed > 0 {
		pctStyle := okStyle
		if m.ContextPct >= 90.0 {
			pctStyle = errStyle
		} else if m.ContextPct >= 70.0 {
			pctStyle = warnStyle
		}
		sb.WriteString(
			dimStyle.Render(fmt.Sprintf("%s/%s", humanTokens(m.ContextUsed), humanTokens(m.ContextWindow)))+
				"  "+pctStyle.Render(fmt.Sprintf("%.0f%%", m.ContextPct))+"\n",
		)
	} else {
		sb.WriteString(dimStyle.Render("—") + "\n")
	}

	if barInnerW > 3 && m.ContextWindow > 0 {
		filled := int(float64(barInnerW) * m.ContextPct / 100.0)
		if filled < 0 {
			filled = 0
		}
		if filled > barInnerW {
			filled = barInnerW
		}
		unfilled := barInnerW - filled
		barColor := "#34D399"
		if m.ContextPct >= 90.0 {
			barColor = "#F87171"
		} else if m.ContextPct >= 70.0 {
			barColor = "#FBBF24"
		}
		barFill := lipgloss.NewStyle().Foreground(lipgloss.Color(barColor))
		barBg   := lipgloss.NewStyle().Foreground(lipgloss.Color("#1E2433"))
		sb.WriteString(barFill.Render(strings.Repeat("▪", filled)) +
			barBg.Render(strings.Repeat("▪", unfilled)) + "\n\n")
	} else {
		sb.WriteString("\n")
	}

	// ── Neuron Quota ──
	sb.WriteString(labelStyle.Render("neurons") + "\n")
	if m.NeuronsQuota > 0 {
		used := m.NeuronsQuota - m.NeuronsRemaining
		pct := 0.0
		if m.NeuronsQuota > 0 {
			pct = float64(used) / float64(m.NeuronsQuota) * 100.0
		}
		nPctStyle := okStyle
		if pct >= 90.0 {
			nPctStyle = errStyle
		} else if pct >= 70.0 {
			nPctStyle = warnStyle
		}
		sb.WriteString(
			dimStyle.Render(fmt.Sprintf("%s used / %s", humanTokens(used), humanTokens(m.NeuronsQuota)))+"\n",
		)
		// Neuron progress bar
		if barInnerW > 3 {
			nFilled := int(float64(barInnerW) * pct / 100.0)
			if nFilled < 0 { nFilled = 0 }
			if nFilled > barInnerW { nFilled = barInnerW }
			nUnfilled := barInnerW - nFilled
			nBarColor := "#34D399"
			if pct >= 90.0 {
				nBarColor = "#F87171"
			} else if pct >= 70.0 {
				nBarColor = "#FBBF24"
			}
			nFillStyle := lipgloss.NewStyle().Foreground(lipgloss.Color(nBarColor))
			nBgStyle   := lipgloss.NewStyle().Foreground(lipgloss.Color("#1E2433"))
			sb.WriteString(nFillStyle.Render(strings.Repeat("▪", nFilled)) +
				nBgStyle.Render(strings.Repeat("▪", nUnfilled)) + "  " +
				nPctStyle.Render(fmt.Sprintf("%.0f%%", pct)) + "\n\n")
		}
	} else {
		sb.WriteString(dimStyle.Render("—") + "\n\n")
	}

	sb.WriteString(divider + "\n\n")

	// ── Active Task ──
	sb.WriteString(labelStyle.Render("active task") + "\n")
	if m.CurrentTask != "" {
		// Wrap task text supaya masuk lebar sidebar
		wrapped := wrapText(m.CurrentTask, w-4)
		sb.WriteString(taskStyle.Render(wrapped) + "\n")
	} else {
		sb.WriteString(dimStyle.Render("idle") + "\n")
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

func wrapText(s string, maxW int) string {
	if maxW <= 0 {
		return s
	}
	runes := []rune(s)
	if len(runes) <= maxW {
		return s
	}
	var lines []string
	for len(runes) > maxW {
		lines = append(lines, string(runes[:maxW]))
		runes = runes[maxW:]
	}
	if len(runes) > 0 {
		lines = append(lines, string(runes))
	}
	return strings.Join(lines, "\n")
}
