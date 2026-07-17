package ui

import "testing"

func TestSidebarUsesCompiledVersion(t *testing.T) {
	t.Setenv("AUTOKEREN_VERSION", "0.11.48")
	if got := NewSidebarModel().Version; got != "v0.11.80" {
		t.Fatalf("unexpected sidebar version: %s", got)
	}
	status := parseStatusReply(map[string]interface{}{"engine": "go"}, "project")
	if status.Version != "v0.11.80" {
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
