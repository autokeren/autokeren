package tool

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
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

type WriteFile struct{ Root string }

func (t WriteFile) Definition() Definition {
	return Definition{Name: "write_file", Description: "Write UTF-8 content to a file inside project root.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"path": map[string]any{"type": "string"}, "content": map[string]any{"type": "string"}}, "required": []string{"path", "content"}}}
}
func (t WriteFile) NeedsPermission(args map[string]any) (bool, string) {
	path, _ := args["path"].(string)
	return true, "Write file: " + path
}
func (t WriteFile) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	path, _ := args["path"].(string)
	content, _ := args["content"].(string)
	target, err := safePath(t.Root, path)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if err := os.WriteFile(target, []byte(content), 0o600); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: fmt.Sprintf("wrote %d bytes", len(content))}
}

type PatchFile struct{ Root string }

func (t PatchFile) Definition() Definition {
	return Definition{Name: "patch_file", Description: "Replace one exact string in a file inside project root.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"path": map[string]any{"type": "string"}, "old_string": map[string]any{"type": "string"}, "new_string": map[string]any{"type": "string"}}, "required": []string{"path", "old_string", "new_string"}}}
}
func (t PatchFile) NeedsPermission(args map[string]any) (bool, string) {
	path, _ := args["path"].(string)
	return true, "Patch file: " + path
}
func (t PatchFile) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	path, _ := args["path"].(string)
	oldString, _ := args["old_string"].(string)
	newString, _ := args["new_string"].(string)
	target, err := safePath(t.Root, path)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	data, err := os.ReadFile(target)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	text := string(data)
	count := strings.Count(text, oldString)
	if count != 1 {
		return Result{OK: false, Error: fmt.Sprintf("expected exactly one match, found %d", count)}
	}
	if err := os.WriteFile(target, []byte(strings.Replace(text, oldString, newString, 1)), 0o600); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: "patched file"}
}
