package tool

import (
	"bytes"
	"context"
	"os/exec"
)

type Shell struct {
	Root           string
	AllowDangerous bool
}

func (t Shell) Definition() Definition {
	return Definition{Name: "run_shell", Description: "Run a shell command in project root.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"command": map[string]any{"type": "string"}}, "required": []string{"command"}}}
}
func (t Shell) NeedsPermission(args map[string]any) (bool, string) {
	command, _ := args["command"].(string)
	return true, "Run shell command: " + command
}
func (t Shell) Run(ctx context.Context, args map[string]any, emit Emitter) Result {
	command, _ := args["command"].(string)
	if command == "" {
		return Result{OK: false, Error: "command is required"}
	}
	cmd := exec.CommandContext(ctx, "sh", "-lc", command)
	cmd.Dir = t.Root
	var output bytes.Buffer
	cmd.Stdout = &output
	cmd.Stderr = &output
	err := cmd.Run()
	text := output.String()
	if emit != nil && text != "" {
		emit(text)
	}
	if err != nil {
		return Result{OK: false, Output: text, Error: err.Error()}
	}
	return Result{OK: true, Output: text}
}
