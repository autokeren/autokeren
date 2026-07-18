package ui

import (
	"strings"
	"testing"
)

func TestRuntimeErrorKeepsInitializedTUIUsable(t *testing.T) {
	m := NewMainModel(nil, nil, ".", "", nil)
	m.Initialized = true
	m.AgentRunning = true
	m.CurrentTask = "Membangun aplikasi"
	m.Sidebar.CurrentTask = m.CurrentTask

	updated, _ := m.Update(ErrorMsg{Message: "provider request: context deadline exceeded"})
	view := updated.(MainModel)

	if view.InitError != "" {
		t.Fatalf("runtime error must not become init error: %q", view.InitError)
	}
	if view.AgentRunning {
		t.Fatal("runtime error must stop the active task")
	}
	if view.CurrentTask != "" || view.Sidebar.CurrentTask != "" {
		t.Fatalf("runtime error must clear active task: %#v / %#v", view.CurrentTask, view.Sidebar.CurrentTask)
	}
	if len(view.Chat.Messages) != 1 || !strings.Contains(view.Chat.Messages[0].Content, "Sesi tetap aktif") {
		t.Fatalf("expected recoverable runtime error message, got %#v", view.Chat.Messages)
	}
}

func TestStartupErrorStillShowsInitializationFailure(t *testing.T) {
	m := NewMainModel(nil, nil, ".", "", nil)

	updated, _ := m.Update(ErrorMsg{Message: "gagal mengambil status awal agen"})
	view := updated.(MainModel)

	if view.InitError == "" {
		t.Fatal("startup error must remain an initialization failure")
	}
}
