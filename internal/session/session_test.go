package session

import (
	"github.com/autokeren/autokeren/internal/model"
	"path/filepath"
	"testing"
)

func TestSaveLoad(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nested", "session.json")
	want := New("abc", []model.Message{{Role: "user", Content: "hi"}})
	if err := Save(path, want); err != nil {
		t.Fatal(err)
	}
	got, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if got.ID != "abc" || len(got.Messages) != 1 {
		t.Fatalf("unexpected %#v", got)
	}
}
