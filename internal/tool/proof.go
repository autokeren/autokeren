package tool

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

type Proof struct{ Root string }
type proofCriterion struct {
	Text       string `json:"text"`
	Status     string `json:"status"`
	Evidence   string `json:"evidence,omitempty"`
	VerifiedAt string `json:"verified_at,omitempty"`
}
type proofData struct {
	ID           string           `json:"id"`
	Title        string           `json:"title"`
	CreatedAt    string           `json:"created_at"`
	SourceCommit string           `json:"source_commit,omitempty"`
	Criteria     []proofCriterion `json:"criteria"`
}

func (p Proof) Definition() Definition {
	return Definition{Name: "proof", Description: "Manage release proof criteria and verdicts.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"plan", "record", "report", "list", "replay"}}, "proof_id": map[string]any{"type": "string"}, "title": map[string]any{"type": "string"}, "criteria": map[string]any{"type": "array"}, "criterion_num": map[string]any{"type": "integer"}, "status": map[string]any{"type": "string"}, "evidence": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (p Proof) NeedsPermission(map[string]any) (bool, string) { return true, "Modify release proof" }
func (p Proof) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	action, _ := args["action"].(string)
	dir := filepath.Join(p.Root, ".autokeren", "proofs")
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if action == "plan" {
		title, _ := args["title"].(string)
		if title == "" {
			return Result{OK: false, Error: "title wajib"}
		}
		var criteria []string
		if raw, ok := args["criteria"].([]any); ok {
			for _, v := range raw {
				if x, ok := v.(string); ok {
					criteria = append(criteria, x)
				}
			}
		}
		if len(criteria) == 0 {
			return Result{OK: false, Error: "criteria wajib"}
		}
		id := fmt.Sprintf("proof-%s", time.Now().UTC().Format("20060102T150405Z"))
		sha := gitSHA(p.Root)
		items := make([]proofCriterion, len(criteria))
		for i, v := range criteria {
			items[i] = proofCriterion{Text: v, Status: "pending"}
		}
		data := proofData{ID: id, Title: title, CreatedAt: time.Now().UTC().Format(time.RFC3339), SourceCommit: sha, Criteria: items}
		if err := writeProof(filepath.Join(dir, id+".json"), data); err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		return Result{OK: true, Output: map[string]any{"proof_id": id, "message": "proof plan created"}}
	}
	switch action {
	case "list":
		entries, _ := os.ReadDir(dir)
		var out []string
		for _, e := range entries {
			if filepath.Ext(e.Name()) == ".json" {
				if d, e2 := loadProof(filepath.Join(dir, e.Name())); e2 == nil {
					out = append(out, fmt.Sprintf("%s — %s [%s]", d.ID, d.Title, verdict(d.Criteria)))
				}
			}
		}
		return Result{OK: true, Output: strings.Join(out, "\n")}
	}
	id, _ := args["proof_id"].(string)
	if action == "replay" {
		id = strings.TrimSpace(id)
	}
	if id == "" {
		return Result{OK: false, Error: "proof_id wajib"}
	}
	path := id
	if action != "replay" {
		if !regexp.MustCompile(`^proof-[A-Za-z0-9T_-]+$`).MatchString(id) {
			return Result{OK: false, Error: "proof_id tidak valid"}
		}
		path = filepath.Join(dir, id+".json")
	}
	data, err := loadProof(path)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	switch action {
	case "record":
		num, _ := args["criterion_num"].(float64)
		idx := int(num) - 1
		status, _ := args["status"].(string)
		valid := map[string]bool{"pending": true, "passed": true, "failed": true, "blocked": true, "manual_review": true}
		if idx < 0 || idx >= len(data.Criteria) || !valid[status] {
			return Result{OK: false, Error: "criterion/status tidak valid"}
		}
		ev, _ := args["evidence"].(string)
		data.Criteria[idx].Status = status
		data.Criteria[idx].Evidence = ev
		data.Criteria[idx].VerifiedAt = time.Now().UTC().Format(time.RFC3339)
		if err := writeProof(filepath.Join(dir, data.ID+".json"), data); err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		return Result{OK: true, Output: map[string]any{"proof_id": data.ID, "verdict": verdict(data.Criteria)}}
	case "report", "replay":
		return Result{OK: true, Output: formatProof(data, action)}
	default:
		return Result{OK: false, Error: "action proof tidak dikenal"}
	}
}
func verdict(items []proofCriterion) string {
	if len(items) == 0 {
		return "IN_PROGRESS"
	}
	all := true
	for _, c := range items {
		if c.Status == "failed" || c.Status == "blocked" {
			return "BLOCKED"
		}
		if c.Status == "manual_review" {
			return "NEEDS_HUMAN_REVIEW"
		}
		if c.Status != "passed" {
			all = false
		}
	}
	if all {
		return "SHIP"
	}
	return "IN_PROGRESS"
}
func formatProof(d proofData, kind string) string {
	out := fmt.Sprintf("AUTOKEREN PROOF %s — %s\n%s\nCommit: %s\n", strings.ToUpper(kind), verdict(d.Criteria), d.Title, d.SourceCommit)
	for i, c := range d.Criteria {
		out += fmt.Sprintf("%d. [%s] %s", i+1, c.Status, c.Text)
		if c.Evidence != "" {
			out += " — " + c.Evidence
		}
		out += "\n"
	}
	return out
}
func gitSHA(root string) string {
	cmd := exec.Command("git", "-C", root, "rev-parse", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}
func writeProof(path string, d proofData) error {
	raw, _ := json.MarshalIndent(d, "", "  ")
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, raw, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}
func loadProof(path string) (proofData, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return proofData{}, err
	}
	var d proofData
	if err := json.Unmarshal(raw, &d); err != nil {
		return d, err
	}
	return d, nil
}
