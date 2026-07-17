package context

import (
	"github.com/autokeren/autokeren/internal/model"
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
