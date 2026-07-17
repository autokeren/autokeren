package ui

import (
	"strings"
	"testing"
)

func TestRenderAssistantTextRemovesMarkdownMarkers(t *testing.T) {
	rendered := renderAssistantText("## Title\n\n**bold** and `code`", 80)
	if strings.Contains(rendered, "**") || strings.Contains(rendered, "`") || strings.Contains(rendered, "##") {
		t.Fatalf("markdown markers leaked: %q", rendered)
	}
	if !strings.Contains(rendered, "Title") || !strings.Contains(rendered, "bold") || !strings.Contains(rendered, "code") {
		t.Fatalf("content missing: %q", rendered)
	}
}

func TestRenderAssistantTextHandlesTablesAndCodeFences(t *testing.T) {
	rendered := renderAssistantText("| File | Status |\n|---|---|\n| **tui.go** | `ok` |\n```go\nfmt.Println(\"ok\")\n```", 80)
	if strings.Contains(rendered, "**") || strings.Contains(rendered, "```") || strings.Contains(rendered, "`ok`") {
		t.Fatalf("markdown markers leaked: %q", rendered)
	}
	if !strings.Contains(rendered, "tui.go") || !strings.Contains(rendered, "fmt.Println") {
		t.Fatalf("content missing: %q", rendered)
	}
}
