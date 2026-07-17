package prompt

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestBuildIncludesProjectGuidanceAndPlanRule(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "AGENTS.md"), []byte("Jalankan go test sebelum commit."), 0o600); err != nil {
		t.Fatal(err)
	}
	value := Build(Options{ProjectRoot: root, ToolNames: []string{"read_file", "write_file"}, PlanMode: true, MaxToolCalls: 7, Language: "Bahasa Indonesia"})
	for _, expected := range []string{"Jalankan go test sebelum commit.", "Mode plan aktif", "maksimal 7", "read_file, write_file"} {
		if !strings.Contains(value, expected) {
			t.Fatalf("prompt missing %q: %s", expected, value)
		}
	}
}

func TestLoadAGENTSLimitsLargeGuidance(t *testing.T) {
	root := t.TempDir()
	value := strings.Repeat("a", maxGuidanceRunes+10)
	if err := os.WriteFile(filepath.Join(root, "AGENTS.md"), []byte(value), 0o600); err != nil {
		t.Fatal(err)
	}
	loaded := LoadAGENTS(root)
	if !strings.Contains(loaded, "dipotong") || len([]rune(loaded)) <= maxGuidanceRunes {
		t.Fatalf("guidance was not bounded: %d", len([]rune(loaded)))
	}
}
