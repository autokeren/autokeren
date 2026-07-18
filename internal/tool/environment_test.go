package tool

import (
	"context"
	"testing"
)

func TestEnvironmentInfoReportsRuntimeCapabilities(t *testing.T) {
	result := (Environment{}).Run(context.Background(), nil, nil)
	if !result.OK {
		t.Fatalf("environment info failed: %#v", result)
	}
	info, ok := result.Output.(map[string]any)
	if !ok || info["os"] == "" || info["shell"] == "" || info["command_style"] == "" {
		t.Fatalf("unexpected environment info: %#v", result.Output)
	}
}
