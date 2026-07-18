package ghost

import (
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
