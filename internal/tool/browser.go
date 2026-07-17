package tool

import (
	"context"
	"encoding/base64"
	"fmt"
	"github.com/autokeren/autokeren/internal/browser"
)

type Browser struct{ Manager *browser.Manager }

func (b Browser) Definition() Definition {
	return Definition{Name: "browser", Description: "Native Go browser automation via Chrome DevTools Protocol.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"navigate", "text", "click", "type", "screenshot", "eval", "status", "close"}}, "session": map[string]any{"type": "string"}, "target": map[string]any{"type": "string"}, "value": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (b Browser) NeedsPermission(args map[string]any) (bool, string) {
	a, _ := args["action"].(string)
	return a != "status", "browser " + a
}
func (b Browser) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	a, _ := args["action"].(string)
	session, _ := args["session"].(string)
	target, _ := args["target"].(string)
	value, _ := args["value"].(string)
	out, err := b.Manager.Run(ctx, session, a, target, value)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if data, ok := out.([]byte); ok {
		return Result{OK: true, Output: map[string]any{"mime": "image/png", "base64": base64.StdEncoding.EncodeToString(data)}}
	}
	return Result{OK: true, Output: out}
}

var _ = fmt.Sprint
