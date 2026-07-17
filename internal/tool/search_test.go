package tool

import (
	"context"
	"os"
	"path/filepath"
	"testing"
)

func TestSearchCode(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "main.go")
	if err := os.WriteFile(path, []byte("package main\nfunc Hello() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	result := (SearchCode{Root: root}).Run(context.Background(), map[string]any{"pattern": "Hello"}, nil)
	if !result.OK {
		t.Fatal(result.Error)
	}
	if len(result.Output.([]string)) != 1 {
		t.Fatalf("unexpected matches: %#v", result.Output)
	}
}
