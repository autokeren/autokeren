package tool

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

type Genome struct{ Root string }

func (g Genome) Definition() Definition {
	return Definition{Name: "genome", Description: "Scan project modules and duplicate functions using native Go.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"view", "rescan", "check"}}}}}
}
func (g Genome) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (g Genome) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	action, _ := args["action"].(string)
	if action == "" {
		action = "view"
	}
	root := g.Root
	if root == "" {
		root = "."
	}
	counts := map[string]int{}
	modules := map[string]int{}
	patterns := []*regexp.Regexp{regexp.MustCompile(`^\s*(?:func|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)`), regexp.MustCompile(`^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)`)}
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		if info.IsDir() {
			for _, ignored := range []string{".git", ".venv", "node_modules", "dist", "build", "__pycache__", ".ak-sessions"} {
				if info.Name() == ignored && path != root {
					return filepath.SkipDir
				}
			}
			return nil
		}
		ext := filepath.Ext(path)
		if ext != ".go" && ext != ".py" && ext != ".js" && ext != ".ts" && ext != ".tsx" {
			return nil
		}
		rel, _ := filepath.Rel(root, path)
		modules[filepath.Dir(rel)]++
		data, readErr := os.ReadFile(path)
		if readErr != nil {
			return nil
		}
		for _, line := range strings.Split(string(data), "\n") {
			for _, pattern := range patterns {
				if match := pattern.FindStringSubmatch(line); len(match) > 1 {
					counts[match[1]]++
					break
				}
			}
		}
		return nil
	})
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	keys := make([]string, 0, len(modules))
	for key := range modules {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	lines := []string{fmt.Sprintf("Project Genome: %d modules, %d indexed symbols", len(modules), len(counts))}
	if action != "check" {
		for _, key := range keys {
			lines = append(lines, fmt.Sprintf("- %s (%d files)", key, modules[key]))
		}
	}
	duplicates := 0
	for name, count := range counts {
		if count > 1 {
			duplicates++
			lines = append(lines, fmt.Sprintf("duplicate: %s (%d)", name, count))
		}
	}
	if action == "check" && duplicates == 0 {
		lines = append(lines, "Tidak ada duplicate function.")
	}
	return Result{OK: true, Output: strings.Join(lines, "\n")}
}
