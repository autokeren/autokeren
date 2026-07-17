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

func TestManagerSaveLoadListAndPartialName(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	manager, err := NewManager(filepath.Join(root, "project"))
	if err != nil {
		t.Fatal(err)
	}
	saved, err := manager.Save("demo-session", []model.Message{{Role: "user", Content: "halo"}}, model.Usage{TotalTokens: 3}, "")
	if err != nil {
		t.Fatal(err)
	}
	loaded, err := manager.Load("demo")
	if err != nil {
		t.Fatal(err)
	}
	if loaded.ID != saved.ID || loaded.Name != "demo-session" || len(loaded.Messages) != 1 || loaded.Usage.TotalTokens != 3 {
		t.Fatalf("unexpected loaded session: %#v", loaded)
	}
	items, err := manager.List()
	if err != nil || len(items) != 1 || items[0].Name != "demo-session" {
		t.Fatalf("unexpected list: %#v err=%v", items, err)
	}
}
