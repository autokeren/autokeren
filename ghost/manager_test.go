package ghost

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestManagerIgnoresLegacyGhostMetadataWithoutPID(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".ak-ghost-1.json"), []byte(`{"id":1,"task":"legacy","status":"running"}`), 0o600); err != nil {
		t.Fatal(err)
	}
	manager := NewGhostManager(root)
	if len(manager.List()) != 0 {
		t.Fatalf("legacy ghost should not be loaded: %#v", manager.List())
	}
}

func TestManagerReservesIDsFromLegacyLogsAndMetadata(t *testing.T) {
	root := t.TempDir()
	for path, content := range map[string]string{
		".ak-ghost-7.log":   "old output",
		".ak-ghost-11.json": `{"id":11,"task":"legacy","status":"completed"}`,
	} {
		if err := os.WriteFile(filepath.Join(root, path), []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	manager := NewGhostManager(root)
	if manager.nextID != 12 {
		t.Fatalf("next ID reused an existing ghost artifact: %d", manager.nextID)
	}
}

func TestRefreshDiscoversGhostCreatedByAnotherRuntimeOwner(t *testing.T) {
	root := t.TempDir()
	manager := NewGhostManager(root)
	metadata, err := json.Marshal(GhostAgentInfo{ID: 4, Task: "delegate", Status: "completed", PID: 1234, LogFile: filepath.Join(root, ".ak-ghost-4.log")})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".ak-ghost-4.json"), []byte(metadata), 0o600); err != nil {
		t.Fatal(err)
	}
	manager.Refresh()
	list := manager.List()
	if len(list) != 1 || list[0].ID != 4 || list[0].Status != "completed" {
		t.Fatalf("refresh did not load external ghost metadata: %#v", list)
	}
}

func TestResolveBinaryPathFindsWindowsExecutableExtension(t *testing.T) {
	path := filepath.Join(t.TempDir(), "autokeren-cli")
	if err := os.WriteFile(path+".exe", []byte("binary"), 0o600); err != nil {
		t.Fatal(err)
	}
	if resolved := resolveBinaryPath(path, true); resolved != path+".exe" {
		t.Fatalf("resolved path = %q", resolved)
	}
}

func TestResolveBinaryPathPrefersWindowsExecutableExtension(t *testing.T) {
	path := filepath.Join(t.TempDir(), "autokeren-cli")
	if err := os.WriteFile(path, []byte("legacy"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path+".exe", []byte("binary"), 0o600); err != nil {
		t.Fatal(err)
	}
	if resolved := resolveBinaryPath(path, true); resolved != path+".exe" {
		t.Fatalf("resolved path = %q", resolved)
	}
}
