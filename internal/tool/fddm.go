package tool

import (
	"context"
	"strings"

	"github.com/autokeren/autokeren/internal/fddm"
)

type FDDM struct{ Client *fddm.Client }

func (f FDDM) Definition() Definition {
	return Definition{Name: "fddm", Description: "Operasi FDDM (Feromon Digital Distributed Memory) untuk memori kolektif antar agent.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"emit", "sniff", "stats", "decay", "trust"}}, "type": map[string]any{"type": "string", "enum": []string{"error", "decision", "document", "conversation", "artifact", "observation"}}, "text": map[string]any{"type": "string"}, "emitter_id": map[string]any{"type": "string"}, "top_k": map[string]any{"type": "integer"}, "radius": map[string]any{"type": "number"}, "success": map[string]any{"type": "boolean"}}, "required": []string{"action"}}}
}

func (f FDDM) NeedsPermission(args map[string]any) (bool, string) {
	action, _ := args["action"].(string)
	return action == "emit" || action == "decay" || action == "trust", "ubah FDDM memory"
}

func (f FDDM) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	if f.Client == nil || !f.Client.Enabled() {
		return Result{OK: false, Error: "FDDM belum dikonfigurasi. Aktifkan fddm.enabled dan isi fddm.url di config.yaml."}
	}
	action, _ := args["action"].(string)
	output, err := f.Client.Execute(ctx, strings.TrimSpace(action), args)
	if err != nil {
		return Result{OK: false, Output: output, Error: err.Error()}
	}
	return Result{OK: true, Output: output}
}
