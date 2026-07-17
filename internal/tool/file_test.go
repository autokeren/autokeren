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

func TestWriteAndPatchFile(t *testing.T) {
	root := t.TempDir()
	writer := WriteFile{Root: root}
	if result := writer.Run(context.Background(), map[string]any{"path": "x.txt", "content": "hello world"}, nil); !result.OK {
		t.Fatal(result.Error)
	}
	patcher := PatchFile{Root: root}
	if result := patcher.Run(context.Background(), map[string]any{"path": "x.txt", "old_string": "world", "new_string": "Go"}, nil); !result.OK {
		t.Fatal(result.Error)
	}
	data, err := os.ReadFile(filepath.Join(root, "x.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "hello Go" {
		t.Fatalf("unexpected content: %s", data)
	}
}
