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
