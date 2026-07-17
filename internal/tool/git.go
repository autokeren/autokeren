package tool

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
)

type GitStatus struct{ Root string }

func (t GitStatus) Definition() Definition {
	return Definition{Name: "git_status", Description: "Show git working tree status.", Parameters: map[string]any{"type": "object"}}
}
func (t GitStatus) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (t GitStatus) Run(ctx context.Context, _ map[string]any, _ Emitter) Result {
	return gitRun(ctx, t.Root, "status", "--short")
}

type GitDiff struct{ Root string }

func (t GitDiff) Definition() Definition {
	return Definition{Name: "git_diff", Description: "Show git diff.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"staged": map[string]any{"type": "boolean"}}}}
}
func (t GitDiff) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (t GitDiff) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	if staged, ok := args["staged"].(bool); ok && staged {
		return gitRun(ctx, t.Root, "diff", "--cached")
	}
	return gitRun(ctx, t.Root, "diff")
}

type GitLog struct{ Root string }

func (t GitLog) Definition() Definition {
	return Definition{Name: "git_log", Description: "Show recent git commits.", Parameters: map[string]any{"type": "object"}}
}
func (t GitLog) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (t GitLog) Run(ctx context.Context, _ map[string]any, _ Emitter) Result {
	return gitRun(ctx, t.Root, "log", "-10", "--oneline", "--decorate")
}

type GitCommit struct{ Root string }

func (t GitCommit) Definition() Definition {
	return Definition{Name: "git_commit", Description: "Create a git commit.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"message": map[string]any{"type": "string"}}, "required": []string{"message"}}}
}
func (t GitCommit) NeedsPermission(args map[string]any) (bool, string) {
	m, _ := args["message"].(string)
	return true, "Create git commit: " + m
}
func (t GitCommit) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	m, _ := args["message"].(string)
	if strings.TrimSpace(m) == "" {
		return Result{OK: false, Error: "message is required"}
	}
	return gitRun(ctx, t.Root, "commit", "-am", m)
}
func gitRun(ctx context.Context, root string, args ...string) Result {
	cmd := exec.CommandContext(ctx, "git", args...)
	cmd.Dir = root
	out, err := cmd.CombinedOutput()
	if err != nil {
		return Result{OK: false, Output: string(out), Error: err.Error()}
	}
	return Result{OK: true, Output: string(out)}
}

var _ = fmt.Sprintf
