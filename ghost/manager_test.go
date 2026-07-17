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
