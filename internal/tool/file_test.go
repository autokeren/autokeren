package tool

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestReadFileBlocksEscape(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "ok.txt"), []byte("hello"), 0o600); err != nil {
		t.Fatal(err)
	}
	result := (ReadFile{Root: root}).Run(context.Background(), map[string]any{"path": "ok.txt"}, nil)
	if !result.OK || result.Output != "hello" {
		t.Fatalf("unexpected result: %#v", result)
	}
	blocked := (ReadFile{Root: root}).Run(context.Background(), map[string]any{"path": "../secret"}, nil)
	if blocked.OK {
		t.Fatalf("path traversal was allowed: %#v", blocked)
	}
}

func TestRegistryRunUnknown(t *testing.T) {
	result := NewRegistry().Run(context.Background(), "missing", nil, nil)
	if result.OK || result.Error == "" {
		t.Fatalf("unexpected result: %#v", result)
	}
}
