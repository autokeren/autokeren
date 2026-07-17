package tool

import (
	"context"
	"fmt"
	"strings"

	"github.com/autokeren/autokeren/ghost"
)

type Collaborate struct{ Manager *ghost.GhostManager }

func (c Collaborate) Definition() Definition {
	return Definition{Name: "collaborate", Description: "Run a native Go coder-critic loop.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"task": map[string]any{"type": "string"}, "coder_role": map[string]any{"type": "string"}, "critic_role": map[string]any{"type": "string"}, "max_turns": map[string]any{"type": "integer"}, "model_id": map[string]any{"type": "string"}}, "required": []string{"task"}}}
}
func (c Collaborate) NeedsPermission(map[string]any) (bool, string) {
	return true, "mulai coder-critic collaboration"
}
func (c Collaborate) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	task, _ := args["task"].(string)
	if strings.TrimSpace(task) == "" {
		return Result{OK: false, Error: "task wajib"}
	}
	coder, _ := args["coder_role"].(string)
	if coder == "" {
		coder = "Expert Go Programmer"
	}
	critic, _ := args["critic_role"].(string)
	if critic == "" {
		critic = "Senior Security Reviewer"
	}
	turns := 3
	if n, ok := args["max_turns"].(float64); ok && n > 0 && n <= 10 {
		turns = int(n)
	}
	modelID, _ := args["model_id"].(string)
	feedback, current := "", ""
	for turn := 1; turn <= turns; turn++ {
		prompt := fmt.Sprintf("Tugas utama: %s\n", task)
		if feedback == "" {
			prompt += "Kerjakan tugas ini dan implementasikan perubahan secara lengkap."
		} else {
			prompt += "Kritik reviewer sebelumnya:\n" + feedback + "\nPerbaiki implementasi berdasarkan kritik tersebut."
		}
		out, err := c.Manager.SpawnSync(ctx, ghost.SpawnOptions{Task: prompt, Role: coder, ModelID: modelID})
		if err != nil {
			return Result{OK: false, Output: out, Error: err.Error()}
		}
		current = out
		criticPrompt := fmt.Sprintf("Tugas: %s\n\nOutput coder:\n%s\n\nReview secara kritis untuk bug, keamanan, test, dan arsitektur. Balas APPROVED jika sudah layak; jika belum, tulis perbaikan konkret.", task, current)
		feedback, err = c.Manager.SpawnSync(ctx, ghost.SpawnOptions{Task: criticPrompt, Role: critic, ModelID: modelID})
		if err != nil {
			return Result{OK: false, Output: feedback, Error: err.Error()}
		}
		if strings.Contains(strings.ToLower(feedback), "approved") || strings.Contains(strings.ToLower(feedback), "passed") {
			break
		}
	}
	return Result{OK: true, Output: fmt.Sprintf("Kolaborasi selesai.\n\nReview akhir:\n%s\n\nOutput coder terakhir:\n%s", feedback, current)}
}
