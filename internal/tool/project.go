package tool

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/autokeren/autokeren/internal/config"
	"net/http"
	"os"
	"strings"
	"time"
)

type CreateProject struct{ Config config.Config }
type DeployProject struct {
	Config config.Config
	Root   string
}
type ListProjects struct{ Config config.Config }

func headers(c config.Config) map[string]string {
	return map[string]string{"Authorization": "Bearer " + c.Auth.APIKey, "Content-Type": "application/json"}
}
func (t CreateProject) Definition() Definition {
	return Definition{Name: "create_project", Description: "Create a project on the Autokeren platform.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"name": map[string]any{"type": "string"}, "description": map[string]any{"type": "string"}}, "required": []string{"name"}}}
}
func (t CreateProject) NeedsPermission(map[string]any) (bool, string) {
	return true, "create project di Autokeren"
}
func (t CreateProject) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	name, _ := args["name"].(string)
	desc, _ := args["description"].(string)
	return platformRequest(ctx, t.Config, http.MethodPost, "/v1/projects", map[string]any{"name": name, "description": desc})
}
func (t DeployProject) Definition() Definition {
	return Definition{Name: "deploy_project", Description: "Deploy Worker code to an Autokeren project.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"project_id": map[string]any{"type": "string"}, "script": map[string]any{"type": "string"}, "file_path": map[string]any{"type": "string"}}, "required": []string{"project_id"}}}
}
func (t DeployProject) NeedsPermission(map[string]any) (bool, string) {
	return true, "deploy project ke Autokeren"
}
func (t DeployProject) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	id, _ := args["project_id"].(string)
	script, _ := args["script"].(string)
	if path, ok := args["file_path"].(string); ok && path != "" {
		target, err := safePath(t.Root, path)
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		data, err := os.ReadFile(target)
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		script = string(data)
	}
	if script == "" {
		return Result{OK: false, Error: "script atau file_path wajib"}
	}
	return platformRequest(ctx, t.Config, http.MethodPost, "/v1/projects/"+id+"/deploy", map[string]any{"script": script})
}
func (t ListProjects) Definition() Definition {
	return Definition{Name: "list_projects", Description: "List Autokeren platform projects.", Parameters: map[string]any{"type": "object"}}
}
func (t ListProjects) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (t ListProjects) Run(ctx context.Context, _ map[string]any, _ Emitter) Result {
	return platformRequest(ctx, t.Config, http.MethodGet, "/v1/projects", nil)
}
func platformRequest(ctx context.Context, c config.Config, method, path string, payload any) Result {
	endpoint := strings.TrimRight(c.Auth.BaseURL, "/") + path
	var body *bytes.Reader
	if payload == nil {
		body = bytes.NewReader(nil)
	} else {
		raw, _ := json.Marshal(payload)
		body = bytes.NewReader(raw)
	}
	req, err := http.NewRequestWithContext(ctx, method, endpoint, body)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	for k, v := range headers(c) {
		req.Header.Set(k, v)
	}
	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	defer resp.Body.Close()
	var data any
	_ = json.NewDecoder(resp.Body).Decode(&data)
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return Result{OK: false, Output: data, Error: fmt.Sprintf("platform HTTP %d", resp.StatusCode)}
	}
	return Result{OK: true, Output: data}
}
