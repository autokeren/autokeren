package tool

import (
	"context"
	"fmt"
	"strings"

	"github.com/autokeren/autokeren/internal/checkpoint"
)

type Rewind struct{ Manager *checkpoint.Manager }

func (r Rewind) Definition() Definition {
	return Definition{Name: "rewind", Description: "Kembalikan perubahan file dari checkpoint terakhir.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"steps": map[string]any{"type": "integer"}}}}
}

func (r Rewind) NeedsPermission(map[string]any) (bool, string) {
	return true, "kembalikan perubahan file dari checkpoint"
}

func (r Rewind) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	if r.Manager == nil {
		return Result{OK: false, Error: "time-travel tidak diaktifkan"}
	}
	steps := numericArg(args["steps"], 1)
	undone, err := r.Manager.Rewind(steps)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if len(undone) == 0 {
		return Result{OK: true, Output: "Tidak ada checkpoint untuk di-rewind."}
	}
	lines := []string{fmt.Sprintf("⏪ Rewind %d tool call:", len(undone))}
	for _, entry := range undone {
		path, _ := entry.ToolArgs["path"].(string)
		lines = append(lines, fmt.Sprintf("  #%d %s(%s) — %d file di-revert", entry.ID, entry.ToolName, path, len(entry.FileChanges)))
	}
	lines = append(lines, fmt.Sprintf("\nCheckpoint tersisa: %d.", r.Manager.Count()))
	return Result{OK: true, Output: strings.Join(lines, "\n")}
}

func numericArg(value any, fallback int) int {
	switch number := value.(type) {
	case int:
		if number > 0 {
			return number
		}
	case int64:
		if number > 0 {
			return int(number)
		}
	case float64:
		if number > 0 {
			return int(number)
		}
	}
	return fallback
}
