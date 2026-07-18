package tool

import (
	"context"

	"github.com/autokeren/autokeren/internal/runtimeenv"
)

type Environment struct{}

func (Environment) Definition() Definition {
	return Definition{Name: "environment_info", Description: "Show the actual operating system, shell syntax, architecture, and detected developer commands.", Parameters: map[string]any{"type": "object"}}
}

func (Environment) NeedsPermission(map[string]any) (bool, string) { return false, "" }

func (Environment) Run(ctx context.Context, _ map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	info := runtimeenv.Current()
	return Result{OK: true, Output: map[string]any{
		"os":                    info.OS,
		"architecture":          info.Architecture,
		"shell":                 info.Shell,
		"command_style":         info.CommandStyle,
		"available_executables": info.AvailableExecutables,
		"missing_executables":   info.MissingExecutables,
	}}
}
