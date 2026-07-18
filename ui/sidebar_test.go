package ui

import (
	"strings"
	"testing"
)

func TestSidebarUsesCompiledVersion(t *testing.T) {
	got := NewSidebarModel().Version
	if !strings.HasPrefix(got, "v") || len(got) <= 1 {
		t.Fatalf("unexpected sidebar version: %s", got)
	}
	status := parseStatusReply(map[string]interface{}{"engine": "go"}, "project")
	if status.Version != got {
		t.Fatalf("unexpected status version: %s", status.Version)
	}
}

func TestSessionChatMessagesHidesInternalMessages(t *testing.T) {
	messages := sessionChatMessages([]interface{}{
		map[string]interface{}{"role": "system", "content": "system prompt"},
		map[string]interface{}{"role": "user", "content": "halo"},
		map[string]interface{}{"role": "tool", "content": "internal"},
		map[string]interface{}{"role": "assistant", "content": "hai"},
	})
	if len(messages) != 2 || messages[0].Content != "halo" || messages[1].Content != "hai" {
		t.Fatalf("unexpected visible messages: %#v", messages)
	}
}

func TestFallbackRetryMessageDoesNotUseZeroAttempt(t *testing.T) {
	m := MainModel{Chat: NewChatModel()}
	updated, _ := m.Update(RetryMsg{Message: "model primary gagal; fallback ke secondary"})
	view := updated.(MainModel)
	if len(view.Chat.Messages) != 1 || view.Chat.Messages[0].Content != "model primary gagal; fallback ke secondary" {
		t.Fatalf("unexpected fallback message: %#v", view.Chat.Messages)
	}
}

func TestSlashMenuHasNoDuplicateCommands(t *testing.T) {
	seen := make(map[string]bool, len(slashCommands))
	for _, command := range slashCommands {
		if seen[command.Name] {
			t.Fatalf("duplicate slash command: %s", command.Name)
		}
		seen[command.Name] = true
	}
	for _, required := range []string{"/genome", "/loop"} {
		if !seen[required] {
			t.Fatalf("missing native slash command: %s", required)
		}
	}
}
