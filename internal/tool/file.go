package tool

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type ReadFile struct{ Root string }

func (t ReadFile) Definition() Definition {
	return Definition{Name: "read_file", Description: "Read a UTF-8 file inside project root.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"path": map[string]any{"type": "string"}}, "required": []string{"path"}}}
}
func (t ReadFile) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (t ReadFile) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	path, _ := args["path"].(string)
	target, err := safePath(t.Root, path)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	data, err := os.ReadFile(target)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: string(data)}
}

type ListFiles struct{ Root string }

func (t ListFiles) Definition() Definition {
	return Definition{Name: "list_files", Description: "List files inside project root.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"path": map[string]any{"type": "string"}}}}
}
func (t ListFiles) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (t ListFiles) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	path, _ := args["path"].(string)
	target, err := safePath(t.Root, path)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	entries, err := os.ReadDir(target)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	names := make([]string, 0, len(entries))
	for _, entry := range entries {
		names = append(names, entry.Name())
	}
	return Result{OK: true, Output: names}
}

func safePath(root, requested string) (string, error) {
	if requested == "" {
		requested = "."
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	targetAbs, err := filepath.Abs(filepath.Join(rootAbs, requested))
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(rootAbs, targetAbs)
	if err != nil || rel == ".." || len(rel) >= 3 && rel[:3] == ".."+string(filepath.Separator) {
		return "", fmt.Errorf("path escapes project root")
	}
	return targetAbs, nil
}

func jsonOutput(value any) string { data, _ := json.Marshal(value); return string(data) }
