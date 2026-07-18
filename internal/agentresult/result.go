package agentresult

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

const maxSummaryRunes = 6000

type ToolEvidence struct {
	Name  string `json:"name"`
	OK    bool   `json:"ok"`
	Error string `json:"error,omitempty"`
	Path  string `json:"path,omitempty"`
	Test  string `json:"test,omitempty"`
}

type Result struct {
	Summary      string         `json:"summary"`
	FilesChanged []string       `json:"files_changed,omitempty"`
	Tests        []ToolEvidence `json:"tests,omitempty"`
	Tools        []ToolEvidence `json:"tools"`
	Blockers     []string       `json:"blockers,omitempty"`
}

func Build(summary string, tools []ToolEvidence) Result {
	files := map[string]struct{}{}
	blockers := map[string]struct{}{}
	tests := make([]ToolEvidence, 0)
	for _, tool := range tools {
		if (tool.Name == "write_file" || tool.Name == "patch_file") && tool.OK && tool.Path != "" {
			files[tool.Path] = struct{}{}
		}
		if tool.Test != "" {
			tests = append(tests, tool)
		}
		if !tool.OK && tool.Error != "" {
			blockers[tool.Error] = struct{}{}
		}
	}
	return Result{Summary: limitRunes(strings.TrimSpace(summary), maxSummaryRunes), FilesChanged: sortedKeys(files), Tests: tests, Tools: tools, Blockers: sortedKeys(blockers)}
}

func Write(path string, result Result) error {
	if strings.TrimSpace(path) == "" {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return err
	}
	temporary := path + ".tmp"
	if err := os.WriteFile(temporary, data, 0o600); err != nil {
		return err
	}
	return os.Rename(temporary, path)
}

func Read(path string) (Result, error) {
	data, err := os.ReadFile(filepath.Clean(path))
	if err != nil {
		return Result{}, err
	}
	var result Result
	if err := json.Unmarshal(data, &result); err != nil {
		return Result{}, err
	}
	return result, nil
}

func sortedKeys(values map[string]struct{}) []string {
	output := make([]string, 0, len(values))
	for value := range values {
		output = append(output, value)
	}
	sort.Strings(output)
	return output
}

func limitRunes(value string, limit int) string {
	runes := []rune(value)
	if len(runes) <= limit {
		return value
	}
	return string(runes[:limit]) + "\n[ringkasan dipotong untuk mailbox director]"
}
