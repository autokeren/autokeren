package tool

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
)

type FDDM struct{ Client *http.Client }

func (f FDDM) Definition() Definition {
	return Definition{Name: "fddm", Description: "Use Feromon Digital Distributed Memory service.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"emit", "sniff", "stats", "decay", "trust"}}, "type": map[string]any{"type": "string"}, "text": map[string]any{"type": "string"}, "emitter_id": map[string]any{"type": "string"}, "top_k": map[string]any{"type": "integer"}, "radius": map[string]any{"type": "number"}, "success": map[string]any{"type": "boolean"}}, "required": []string{"action"}}}
}
func (f FDDM) NeedsPermission(args map[string]any) (bool, string) {
	a, _ := args["action"].(string)
	return a == "emit" || a == "decay" || a == "trust", "ubah FDDM memory"
}
func (f FDDM) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	base := strings.TrimRight(os.Getenv("FDDM_URL"), "/")
	if base == "" {
		base = "https://fddm.autokeren.workers.dev"
	}
	action, _ := args["action"].(string)
	payload := map[string]any{"type": getString(args, "type"), "text": getString(args, "text"), "emitter_id": getString(args, "emitter_id"), "top_k": args["top_k"], "radius": args["radius"], "success": args["success"]}
	path := "/api/" + action
	method := http.MethodPost
	if action == "stats" {
		method, path = http.MethodGet, "/api/stats"
	}
	if action == "emit" {
		path = "/api/emit_text"
	}
	if action == "sniff" {
		path = "/api/sniff_text"
	}
	if action != "emit" && action != "sniff" && action != "stats" && action != "decay" && action != "trust" {
		return Result{OK: false, Error: "aksi FDDM tidak dikenal"}
	}
	var body *bytes.Reader
	data, _ := json.Marshal(payload)
	body = bytes.NewReader(data)
	req, err := http.NewRequestWithContext(ctx, method, base+path, body)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	req.Header.Set("Content-Type", "application/json")
	if key := os.Getenv("FDDM_API_KEY"); key != "" {
		req.Header.Set("Authorization", "Bearer "+key)
	}
	client := f.Client
	if client == nil {
		client = &http.Client{}
	}
	resp, err := client.Do(req)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	defer resp.Body.Close()
	var out any
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if resp.StatusCode >= 400 {
		return Result{OK: false, Output: out, Error: fmt.Sprintf("FDDM HTTP %d", resp.StatusCode)}
	}
	return Result{OK: true, Output: out}
}
