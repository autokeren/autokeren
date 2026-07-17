package tool

import (
	"context"
	"strings"

	"github.com/autokeren/autokeren/internal/memory"
)

type Remember struct{ Root string }

func (r Remember) Definition() Definition {
	return Definition{Name: "remember", Description: "Save a useful note for future sessions.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"section": map[string]any{"type": "string"}, "note": map[string]any{"type": "string"}}, "required": []string{"section", "note"}}}
}
func (r Remember) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (r Remember) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	section, _ := args["section"].(string)
	note, _ := args["note"].(string)
	if strings.TrimSpace(section) == "" || strings.TrimSpace(note) == "" {
		return Result{OK: false, Error: "section dan note wajib"}
	}
	if err := memory.New(r.Root).Append(section, note); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: "tersimpan di memory [" + section + "]"}
}
