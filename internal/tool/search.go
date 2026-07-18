package tool

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/autokeren/autokeren/internal/safety"
)

type SearchCode struct{ Root string }

func (t SearchCode) Definition() Definition {
	return Definition{Name: "search_code", Description: "Search text or regex in project files.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"pattern": map[string]any{"type": "string"}, "path": map[string]any{"type": "string"}, "file_glob": map[string]any{"type": "string"}, "case_sensitive": map[string]any{"type": "boolean"}}, "required": []string{"pattern"}}}
}
func (t SearchCode) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (t SearchCode) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	pattern, _ := args["pattern"].(string)
	if pattern == "" {
		return Result{OK: false, Error: "pattern is required"}
	}
	root := t.Root
	if path, ok := args["path"].(string); ok && path != "" {
		var err error
		root, err = safePath(t.Root, path)
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
	}
	glob := "*"
	if v, ok := args["file_glob"].(string); ok && v != "" {
		glob = v
	}
	sensitive := true
	if v, ok := args["case_sensitive"].(bool); ok {
		sensitive = v
	}
	expr := pattern
	if !sensitive {
		expr = "(?i)" + expr
	}
	re, err := regexp.Compile(expr)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	var out []string
	err = filepath.Walk(root, func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		if info.IsDir() {
			if path != root && (info.Name() == ".git" || info.Name() == "node_modules" || info.Name() == ".venv") {
				return filepath.SkipDir
			}
			return nil
		}
		if ok, _ := filepath.Match(glob, info.Name()); !ok {
			return nil
		}
		if blocked, _ := safety.ValidateRead(path); blocked {
			return nil
		}
		if needsPermission, _ := safety.NeedsReadPermission(path); needsPermission {
			return nil
		}
		f, e := os.Open(path)
		if e != nil {
			return nil
		}
		defer f.Close()
		scanner := bufio.NewScanner(f)
		line := 0
		for scanner.Scan() {
			line++
			if re.MatchString(scanner.Text()) {
				rel, _ := filepath.Rel(t.Root, path)
				out = append(out, fmt.Sprintf("%s:%d:%s", rel, line, strings.TrimSpace(scanner.Text())))
			}
		}
		return scanner.Err()
	})
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: out}
}
