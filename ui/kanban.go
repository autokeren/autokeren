package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/lipgloss"
)

func (m MainModel) KanbanView(panelWidth int, panelHeight int) string {
	var todoTasks []KanbanTask
	var progressTasks []KanbanTask
	var doneTasks []KanbanTask

	for _, t := range m.KanbanTasks {
		switch t.Status {
		case "todo":
			todoTasks = append(todoTasks, t)
		case "in_progress":
			progressTasks = append(progressTasks, t)
		case "done":
			doneTasks = append(doneTasks, t)
		}
	}

	colWidth := (panelWidth - 6) / 3
	if colWidth < 22 {
		colWidth = 22
	}

	todoHeaderStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#38BDF8")).Bold(true)
	progressHeaderStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)
	doneHeaderStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#34D399")).Bold(true)

	colStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#2D3748")).
		Padding(1, 1).
		Width(colWidth).
		Height(panelHeight - 6)

	todoContent := renderColumnContent(todoTasks, 0, m.SelectedColumn, m.SelectedTaskIndex, colWidth)
	progressContent := renderColumnContent(progressTasks, 1, m.SelectedColumn, m.SelectedTaskIndex, colWidth)
	doneContent := renderColumnContent(doneTasks, 2, m.SelectedColumn, m.SelectedTaskIndex, colWidth)

	todoCol := colStyle.BorderForeground(lipgloss.Color("#38BDF8")).Render(
		todoHeaderStyle.Render(fmt.Sprintf("🎯 TODO (%d)", len(todoTasks))) + "\n\n" + todoContent,
	)
	progressCol := colStyle.BorderForeground(lipgloss.Color("#FBBF24")).Render(
		progressHeaderStyle.Render(fmt.Sprintf("⚡ IN PROGRESS (%d)", len(progressTasks))) + "\n\n" + progressContent,
	)
	doneCol := colStyle.BorderForeground(lipgloss.Color("#34D399")).Render(
		doneHeaderStyle.Render(fmt.Sprintf("✅ DONE (%d)", len(doneTasks))) + "\n\n" + doneContent,
	)

	columnsView := lipgloss.JoinHorizontal(lipgloss.Top, todoCol, progressCol, doneCol)

	var overlay string
	if m.KanbanAddingTask {
		overlay = renderAddDialog(m.KanbanInputTitle, panelWidth)
	}

	footerStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6B7280")).
		Italic(true).
		PaddingTop(1)

	footer := footerStyle.Render(
		"  ↑↓/←→: Pilih Kartu  ·  Space: Pindahkan  ·  a: Tambah  ·  d: Hapus  ·  Tab/Ctrl+K: Kembali ke Chat",
	)

	if overlay != "" {
		return lipgloss.JoinVertical(lipgloss.Left, columnsView, overlay, footer)
	}
	return lipgloss.JoinVertical(lipgloss.Left, columnsView, footer)
}

func renderColumnContent(tasks []KanbanTask, colID int, selectedCol int, selectedTaskIndex int, width int) string {
	if len(tasks) == 0 {
		return lipgloss.NewStyle().Foreground(lipgloss.Color("#4B5563")).Italic(true).Render("   (kosong)")
	}

	var sb strings.Builder
	cardStyle := lipgloss.NewStyle().
		Border(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color("#1E2433")).
		Padding(0, 1).
		Width(width - 4)

	activeCardStyle := cardStyle.
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#A78BFA")).
		Bold(true)

	for i, t := range tasks {
		isHovered := (colID == selectedCol && i == selectedTaskIndex)
		
		priorityStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#94A3B8"))
		if t.Priority == "high" {
			priorityStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#F87171")).Bold(true)
		} else if t.Priority == "medium" {
			priorityStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24"))
		}

		cardTitle := t.Title
		if len([]rune(cardTitle)) > width-8 {
			cardTitle = string([]rune(cardTitle)[:width-11]) + "..."
		}

		var cardContent string
		if isHovered {
			cardContent = activeCardStyle.Render(
				fmt.Sprintf("🌟 #%d %s\n   pri: %s", t.ID, cardTitle, priorityStyle.Render(strings.ToUpper(t.Priority))),
			)
		} else {
			cardContent = cardStyle.Render(
				fmt.Sprintf(" #%d %s\n   pri: %s", t.ID, cardTitle, priorityStyle.Render(strings.ToUpper(t.Priority))),
			)
		}
		sb.WriteString(cardContent + "\n")
	}

	return sb.String()
}

func renderAddDialog(input textinput.Model, width int) string {
	dialogStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#FBBF24")).
		Padding(1, 2).
		Width(width - 4)

	titleStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#FBBF24")).Bold(true)

	var sb strings.Builder
	sb.WriteString(titleStyle.Render("➕ Tambah Tugas Kanban Baru") + "\n")
	sb.WriteString(input.View() + "\n\n")
	sb.WriteString(lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280")).Render("Tekan Enter untuk menyimpan, Esc untuk membatalkan."))

	return dialogStyle.Render(sb.String())
}
