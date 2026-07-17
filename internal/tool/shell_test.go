package tool

import (
	"context"
	"testing"
)

func TestShellRun(t *testing.T) {
	result := (Shell{Root: t.TempDir()}).Run(context.Background(), map[string]any{"command": "printf hello"}, nil)
	if !result.OK || result.Output != "hello" {
		t.Fatalf("unexpected result: %#v", result)
	}
}
