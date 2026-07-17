package tool

import (
	"context"
	"fmt"
	"os/exec"
	"regexp"
	"strings"
)

type Review struct{ Root string }

func (r Review) Definition() Definition {
	return Definition{Name: "review", Description: "Review current git diff for correctness and common risks.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"diff": map[string]any{"type": "string"}}}}
}
func (r Review) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (r Review) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	diff, _ := args["diff"].(string)
	if diff == "" {
		cmd := exec.CommandContext(ctx, "git", "diff")
		cmd.Dir = r.Root
		out, err := cmd.Output()
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		diff = string(out)
	}
	if strings.TrimSpace(diff) == "" {
		return Result{OK: true, Output: "Tidak ada perubahan untuk direview."}
	}
	findings := []string{}
	for _, line := range strings.Split(diff, "\n") {
		if strings.HasPrefix(line, "+") && !strings.HasPrefix(line, "+++") {
			if regexp.MustCompile(`(?i)(api[_-]?key|password|secret|token)\s*[:=]`).MatchString(line) {
				findings = append(findings, "potential secret: "+strings.TrimSpace(line))
			}
		}
	}
	summary := fmt.Sprintf("Review diff: %d baris perubahan", len(strings.Split(diff, "\n")))
	if len(findings) > 0 {
		summary += "\nWarnings:\n- " + strings.Join(findings, "\n- ")
	} else {
		summary += "\nTidak ditemukan pola secret sederhana."
	}
	return Result{OK: true, Output: summary}
}

type SecurityScan struct{ Root string }

func (s SecurityScan) Definition() Definition {
	return Definition{Name: "security_scan", Description: "Scan project files for obvious credential leaks.", Parameters: map[string]any{"type": "object"}}
}
func (s SecurityScan) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (s SecurityScan) Run(ctx context.Context, _ map[string]any, _ Emitter) Result {
	return (SearchCode{Root: s.Root}).Run(ctx, map[string]any{"pattern": "(?i)(api[_-]?key|password|secret|token)\\s*[:=]"}, nil)
}
