package tool

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

type CFDeploy struct{ Root string }

func (c CFDeploy) Definition() Definition {
	return Definition{Name: "cf_deploy", Description: "Deploy to Cloudflare Pages or Workers using wrangler.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"target": map[string]any{"type": "string", "enum": []string{"pages", "worker"}}, "path": map[string]any{"type": "string"}, "project_name": map[string]any{"type": "string"}, "worker_name": map[string]any{"type": "string"}}, "required": []string{"target"}}}
}
func (c CFDeploy) NeedsPermission(args map[string]any) (bool, string) {
	target, _ := args["target"].(string)
	return true, "deploy " + target + " ke Cloudflare"
}
func (c CFDeploy) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	target, _ := args["target"].(string)
	path, _ := args["path"].(string)
	if path == "" {
		path = "."
	}
	cwd, err := safePath(c.Root, path)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	var cmd *exec.Cmd
	switch target {
	case "pages":
		name, _ := args["project_name"].(string)
		if name == "" {
			return Result{OK: false, Error: "project_name required"}
		}
		cmd = exec.CommandContext(ctx, "npx", "wrangler", "pages", "deploy", "--project-name", name, cwd)
	case "worker":
		cmd = exec.CommandContext(ctx, "npx", "wrangler", "deploy")
		cmd.Dir = cwd
	default:
		return Result{OK: false, Error: "target must be pages or worker"}
	}
	if cmd.Dir == "" {
		cmd.Dir = cwd
	}
	out, err := runCommand(cmd, 5*time.Minute)
	if err != nil {
		return Result{OK: false, Output: out, Error: err.Error()}
	}
	return Result{OK: true, Output: out}
}

type CFBuild struct{ Root string }

func (c CFBuild) Definition() Definition {
	return Definition{Name: "cf_build_next", Description: "Build a Next.js app for Cloudflare Pages.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"path": map[string]any{"type": "string"}, "package_manager": map[string]any{"type": "string", "enum": []string{"npm", "pnpm", "yarn"}}}}}
}
func (c CFBuild) NeedsPermission(map[string]any) (bool, string) {
	return true, "build aplikasi Cloudflare"
}
func (c CFBuild) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	path, _ := args["path"].(string)
	if path == "" {
		path = "."
	}
	cwd, err := safePath(c.Root, path)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	pm, _ := args["package_manager"].(string)
	if pm == "" {
		pm = "npm"
	}
	cmd := exec.CommandContext(ctx, pm, "run", "pages:build")
	cmd.Dir = cwd
	out, err := runCommand(cmd, 5*time.Minute)
	if err != nil {
		return Result{OK: false, Output: out, Error: err.Error()}
	}
	return Result{OK: true, Output: out}
}
func runCommand(cmd *exec.Cmd, timeout time.Duration) (string, error) {
	done := make(chan error, 1)
	var data []byte
	go func() { var err error; data, err = cmd.CombinedOutput(); done <- err }()
	select {
	case err := <-done:
		return strings.TrimSpace(string(data)), err
	case <-time.After(timeout):
		_ = cmd.Process.Kill()
		return string(data), fmt.Errorf("command timeout")
	}
}
