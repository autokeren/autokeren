package context

import (
	"github.com/autokeren/autokeren/internal/model"
	"strings"
	"testing"
)

func TestStoreCompacts(t *testing.T) {
	s := New(20, true, 0.5)
	s.Add(model.Message{Role: "system", Content: "rules"})
	s.Add(model.Message{Role: "user", Content: "this is a long message that forces compaction"})
	s.Add(model.Message{Role: "assistant", Content: "another long response"})
	if len(s.Messages()) != 3 {
		t.Fatalf("expected compacted messages, got %d", len(s.Messages()))
	}
}

func TestStoreManualCompactPreservesConfiguredTail(t *testing.T) {
	s := New(262144, false, 0.6)
	s.SetCompactTail(2)
	s.Replace([]model.Message{
		{Role: "system", Content: "rules"},
		{Role: "user", Content: "old"},
		{Role: "assistant", Content: "old response"},
		{Role: "user", Content: "recent question"},
		{Role: "assistant", Content: "recent response"},
	})
	_, _, changed := s.Compact()
	messages := s.Messages()
	if !changed || len(messages) != 4 || messages[2].Content != "recent question" || messages[3].Content != "recent response" {
		t.Fatalf("unexpected compacted context: %#v", messages)
	}
}

func TestStoreCompactKeepsStructuredSummary(t *testing.T) {
	s := New(262144, false, 0.6)
	s.SetCompactTail(1)
	s.Replace([]model.Message{
		{Role: "system", Content: "rules"},
		{Role: "user", Content: "perbaiki router retry"},
		{Role: "assistant", Content: "router diperbarui"},
		{Role: "user", Content: "lanjut test"},
	})
	_, _, changed := s.Compact()
	messages := s.Messages()
	if !changed || len(messages) != 3 || !strings.Contains(messages[1].Content, "perbaiki router retry") || messages[2].Content != "lanjut test" {
		t.Fatalf("unexpected compacted context: %#v", messages)
	}
}

func TestStoreCompactsForReservedResponseBudgetWithoutAutoCompact(t *testing.T) {
	s := New(200, false, 0.6)
	s.SetCompactTail(1)
	s.Replace([]model.Message{
		{Role: "system", Content: "rules"},
		{Role: "user", Content: strings.Repeat("a", 400)},
		{Role: "assistant", Content: strings.Repeat("b", 400)},
		{Role: "user", Content: strings.Repeat("c", 400)},
	})
	s.SetReserveTokens(120)
	messages := s.Messages()
	if len(messages) != 3 || !strings.Contains(messages[1].Content, "Ringkasan context lama") || messages[2].Content != strings.Repeat("c", 400) {
		t.Fatalf("reserved response budget did not compact context: %#v", messages)
	}
}
