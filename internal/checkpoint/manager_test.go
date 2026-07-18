package checkpoint

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestManagerRestoresFileChangesInReverseOrder(t *testing.T) {
	root := t.TempDir()
	manager, err := New(root, "default", 50, true)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, "app.txt")
	first := manager.Snapshot("write_file", map[string]any{"path": "app.txt"})
	if err := os.WriteFile(path, []byte("v1"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.Save("write_file", map[string]any{"path": "app.txt"}, map[string]any{"ok": true}, true, first); err != nil {
		t.Fatal(err)
	}
	second := manager.Snapshot("patch_file", map[string]any{"path": "app.txt"})
	if err := os.WriteFile(path, []byte("v2"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.Save("patch_file", map[string]any{"path": "app.txt"}, map[string]any{"ok": true}, true, second); err != nil {
		t.Fatal(err)
	}
	undone, err := manager.Rewind(1)
	if err != nil || len(undone) != 1 {
		t.Fatalf("rewind patch = %#v err=%v", undone, err)
	}
	data, err := os.ReadFile(path)
	if err != nil || string(data) != "v1" {
		t.Fatalf("rewind patch tidak memulihkan file: %q err=%v", data, err)
	}
	undone, err = manager.Rewind(1)
	if err != nil || len(undone) != 1 {
		t.Fatalf("rewind create = %#v err=%v", undone, err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("file baru harus dihapus saat rewind create: %v", err)
	}
}

func TestManagerReadsPythonCompatibleCheckpointFixture(t *testing.T) {
	root := t.TempDir()
	manager, err := New(root, "default", 50, true)
	if err != nil {
		t.Fatal(err)
	}
	content := "dibuat oleh checkpoint Python"
	fixture := map[string]any{
		"id":           1,
		"timestamp":    123.5,
		"tool_name":    "write_file",
		"tool_args":    map[string]any{"path": "fixture.txt"},
		"tool_result":  map[string]any{"ok": true},
		"tool_ok":      true,
		"file_changes": []map[string]any{{"path": "fixture.txt", "action": "create", "before": nil, "after": content}},
	}
	data, err := json.Marshal(fixture)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(manager.Directory(), "0001.json"), data, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "fixture.txt"), []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	entries, err := manager.List()
	if err != nil || len(entries) != 1 || entries[0].ToolName != "write_file" {
		t.Fatalf("fixture Python tidak terbaca: %#v err=%v", entries, err)
	}
	undone, err := manager.Rewind(1)
	if err != nil || len(undone) != 1 {
		t.Fatalf("fixture Python tidak dapat di-rewind: %#v err=%v", undone, err)
	}
	if _, err := os.Stat(filepath.Join(root, "fixture.txt")); !os.IsNotExist(err) {
		t.Fatalf("file fixture masih ada: %v", err)
	}
}
