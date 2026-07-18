package tool

import (
	"context"
	"strings"
	"testing"
)

func TestShellRun(t *testing.T) {
	result := (Shell{Root: t.TempDir()}).Run(context.Background(), map[string]any{"command": "go version"}, nil)
	output, _ := result.Output.(string)
	if !result.OK || !strings.Contains(output, "go version") {
		t.Fatalf("unexpected result: %#v", result)
	}
}
