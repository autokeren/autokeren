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

type GitBranch struct{ Root string }

func (t GitBranch) Definition() Definition {
	return Definition{Name: "git_branch", Description: "List, create, or switch git branches.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"list", "create", "switch", "create_and_switch"}}, "name": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (t GitBranch) NeedsPermission(args map[string]any) (bool, string) {
	a, _ := args["action"].(string)
	return a != "list", "Change git branch"
}
func (t GitBranch) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	a, _ := args["action"].(string)
	name, _ := args["name"].(string)
	switch a {
	case "list":
		return gitRun(ctx, t.Root, "branch", "-a")
	case "create":
		if name == "" {
			return Result{OK: false, Error: "branch name is required"}
		}
		return gitRun(ctx, t.Root, "branch", name)
	case "switch":
		if name == "" {
			return Result{OK: false, Error: "branch name is required"}
		}
		return gitRun(ctx, t.Root, "switch", name)
	case "create_and_switch":
		if name == "" {
			return Result{OK: false, Error: "branch name is required"}
		}
		return gitRun(ctx, t.Root, "switch", "-c", name)
	default:
		return Result{OK: false, Error: "unknown branch action"}
	}
}

type GitAutoCommit struct{ Root string }

func (t GitAutoCommit) Definition() Definition {
	return Definition{Name: "git_auto_commit", Description: "Stage selected files and create a conventional commit.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"files": map[string]any{"type": "array"}, "summary": map[string]any{"type": "string"}}, "required": []string{"files", "summary"}}}
}
func (t GitAutoCommit) NeedsPermission(map[string]any) (bool, string) {
	return true, "Create automatic git commit"
}
func (t GitAutoCommit) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	files, _ := args["files"].([]any)
	summary, _ := args["summary"].(string)
	if strings.TrimSpace(summary) == "" {
		return Result{OK: false, Error: "summary is required"}
	}
	if len(files) == 0 {
		return Result{OK: true, Output: "Tidak ada file untuk di-commit."}
	}
	paths := make([]string, 0, len(files))
	for _, raw := range files {
		if path, ok := raw.(string); ok && path != "" {
			paths = append(paths, path)
		}
	}
	if len(paths) == 0 {
		return Result{OK: true, Output: "Tidak ada file untuk di-commit."}
	}
	addArgs := append([]string{"add", "--"}, paths...)
	if result := gitRun(ctx, t.Root, addArgs...); !result.OK {
		return result
	}
	return gitRun(ctx, t.Root, "commit", "-m", "feat: "+summary)
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
