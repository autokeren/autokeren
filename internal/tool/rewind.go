package tool

import (
	"context"
	"fmt"
	"github.com/autokeren/autokeren/internal/session"
	"path/filepath"
)

type Rewind struct{ Root string }

func (r Rewind) Definition() Definition {
	return Definition{Name: "rewind", Description: "Rewind the saved Go conversation by a number of turns.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"steps": map[string]any{"type": "integer"}}}}
}
func (r Rewind) NeedsPermission(map[string]any) (bool, string) { return true, "rewind conversation" }
func (r Rewind) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	steps := 1
	if v, ok := args["steps"].(float64); ok && v > 0 {
		steps = int(v)
	}
	path := filepath.Join(r.Root, ".ak-sessions", "tui.json")
	data, err := session.Load(path)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	remove := steps * 2
	if remove >= len(data.Messages) {
		remove = len(data.Messages) - 1
	}
	if remove < 1 {
		return Result{OK: false, Error: "tidak ada turn untuk di-rewind"}
	}
	data.Messages = data.Messages[:len(data.Messages)-remove]
	if err := session.Save(path, data); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: fmt.Sprintf("rewind %d turn berhasil", steps)}
}
