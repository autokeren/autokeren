package tool

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/autokeren/autokeren/internal/safety"
)

type ReadFile struct{ Root string }

func (t ReadFile) Definition() Definition {
	return Definition{Name: "read_file", Description: "Read a UTF-8 file inside project root.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"path": map[string]any{"type": "string"}}, "required": []string{"path"}}}
}
func (t ReadFile) NeedsPermission(args map[string]any) (bool, string) {
	path, _ := args["path"].(string)
	target, err := safePath(t.Root, path)
	if err != nil {
		return false, ""
	}
	return safety.NeedsReadPermission(target)
}
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
	if blocked, reason := safety.ValidateRead(target); blocked {
		return Result{OK: false, Error: reason}
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
	return safety.ProjectPath(root, requested)
}

type WriteFile struct {
	Root  string
	Guard *safety.Guard
}

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
	if err := safety.ValidateWriteTarget(target); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	warnings, err := validateWrite(t.Guard, path, content)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if err := writeAtomic(target, []byte(content)); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if t.Guard != nil {
		t.Guard.RecordWrite(path, content)
	}
	return Result{OK: true, Output: writeOutput(fmt.Sprintf("wrote %d bytes", len(content)), warnings)}
}

type PatchFile struct {
	Root  string
	Guard *safety.Guard
}

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
	if err := safety.ValidateWriteTarget(target); err != nil {
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
	updated := strings.Replace(text, oldString, newString, 1)
	warnings, err := validateWrite(t.Guard, path, updated)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if err := writeAtomic(target, []byte(updated)); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if t.Guard != nil {
		t.Guard.RecordWrite(path, updated)
	}
	return Result{OK: true, Output: writeOutput("patched file", warnings)}
}

func validateWrite(guard *safety.Guard, path, content string) ([]string, error) {
	if guard == nil {
		return nil, nil
	}
	return guard.Validate(path, content)
}

func writeOutput(base string, warnings []string) string {
	if len(warnings) == 0 {
		return base
	}
	return base + "\nPeringatan:\n- " + strings.Join(warnings, "\n- ")
}

func writeAtomic(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	if info, err := os.Stat(path); err == nil && info.Mode().IsRegular() {
		backup := path + ".bak-" + time.Now().UTC().Format("20060102-150405.000000000")
		original, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		if err := os.WriteFile(backup, original, 0o600); err != nil {
			return err
		}
	}
	file, err := os.CreateTemp(filepath.Dir(path), ".autokeren-write-")
	if err != nil {
		return err
	}
	temporary := file.Name()
	defer os.Remove(temporary)
	if err := file.Chmod(0o600); err != nil {
		file.Close()
		return err
	}
	if _, err := file.Write(data); err != nil {
		file.Close()
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	return os.Rename(temporary, path)
}
