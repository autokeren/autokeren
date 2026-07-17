package tool

import (
	"context"
	"github.com/autokeren/autokeren/internal/browser"
)

type Browser struct{ Manager *browser.BrowserManager }

func (b Browser) Definition() Definition {
	return Definition{Name: "browser", Description: "Native Go browser automation via Chrome DevTools Protocol (Rod).", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"navigate", "snapshot", "click", "type", "screenshot", "eval", "assert", "close"}}, "url": map[string]any{"type": "string"}, "selector": map[string]any{"type": "string"}, "ref": map[string]any{"type": "integer"}, "text": map[string]any{"type": "string"}, "expression": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (b Browser) NeedsPermission(args map[string]any) (bool, string) {
	a, _ := args["action"].(string)
	return a != "snapshot" && a != "assert", "browser " + a
}
func (b Browser) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	a, _ := args["action"].(string)
	out, err := b.Manager.Execute(a, args)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: out}
}
