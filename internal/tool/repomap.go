package tool

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

type RepoMap struct{ Root string }

func (r RepoMap) Definition() Definition {
	return Definition{Name: "repo_map", Description: "Generate a compact structural map of project files and symbols.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"max_files": map[string]any{"type": "integer"}, "query": map[string]any{"type": "string"}}}}
}
func (r RepoMap) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (r RepoMap) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	max := 15
	if v, ok := args["max_files"].(float64); ok && v > 0 {
		max = int(v)
	}
	query, _ := args["query"].(string)
	var files []string
	err := filepath.Walk(r.Root, func(path string, info os.FileInfo, e error) error {
		if e != nil {
			return e
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		if info.IsDir() {
			switch info.Name() {
			case ".git", ".venv", "node_modules", "dist", "build", "__pycache__":
				return filepath.SkipDir
			}
			return nil
		}
		ext := filepath.Ext(path)
		if ext == ".go" || ext == ".py" || ext == ".ts" || ext == ".js" {
			files = append(files, path)
		}
		return nil
	})
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	sort.Strings(files)
	if query != "" {
		q := strings.ToLower(query)
		filtered := files[:0]
		for _, f := range files {
			if strings.Contains(strings.ToLower(f), q) {
				filtered = append(filtered, f)
			}
		}
		files = filtered
	}
	if len(files) > max {
		files = files[:max]
	}
	out := strings.Builder{}
	for _, f := range files {
		rel, _ := filepath.Rel(r.Root, f)
		out.WriteString("- " + rel + "\n")
		symbols, err := symbolsInFile(f)
		if err == nil {
			for _, sym := range symbols {
				out.WriteString("  " + sym + "\n")
			}
		}
	}
	return Result{OK: true, Output: out.String()}
}
func symbolsInFile(path string) ([]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var out []string
	re := regexp.MustCompile(`^\s*(func|def|class|type)\s+([A-Za-z0-9_]+)`)
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		m := re.FindStringSubmatch(scanner.Text())
		if len(m) > 0 {
			out = append(out, m[1]+" "+m[2])
		}
	}
	return out, scanner.Err()
}

var _ = fmt.Sprintf
