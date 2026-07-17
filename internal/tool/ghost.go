package tool

import (
	"context"
	"fmt"
	"github.com/autokeren/autokeren/ghost"
	"strings"
)

type SpawnGhost struct{ Manager *ghost.GhostManager }

func (s SpawnGhost) Definition() Definition {
	return Definition{Name: "spawn_agent", Description: "Spawn a native Go sub-agent in background or synchronously.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"task": map[string]any{"type": "string"}, "context": map[string]any{"type": "string"}, "role": map[string]any{"type": "string"}, "model_id": map[string]any{"type": "string"}, "background": map[string]any{"type": "boolean"}, "agent_name": map[string]any{"type": "string"}}, "required": []string{"task"}}}
}
func (s SpawnGhost) NeedsPermission(map[string]any) (bool, string) {
	return true, "spawn native Go ghost agent"
}
func (s SpawnGhost) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	task, _ := args["task"].(string)
	if task == "" {
		return Result{OK: false, Error: "task wajib"}
	}
	options := ghost.SpawnOptions{Task: task}
	options.Context, _ = args["context"].(string)
	options.Role, _ = args["role"].(string)
	options.ModelID, _ = args["model_id"].(string)
	background, _ := args["background"].(bool)
	if !background {
		output, err := s.Manager.SpawnSync(ctx, options)
		if err != nil {
			return Result{OK: false, Output: output, Error: err.Error()}
		}
		return Result{OK: true, Output: output}
	}
	info, err := s.Manager.SpawnWithOptions(options)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: fmt.Sprintf("ghost #%d started", info.ID)}
}

type CheckGhost struct{ Manager *ghost.GhostManager }

func (c CheckGhost) Definition() Definition {
	return Definition{Name: "check_agent", Description: "Check native Go ghost agents.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"agent_id": map[string]any{"type": "integer"}}}}
}
func (c CheckGhost) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (c CheckGhost) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	if v, ok := args["agent_id"].(float64); ok {
		id := int(v)
		status := c.Manager.CheckStatus(id)
		for _, info := range c.Manager.List() {
			if info.ID == id {
				return Result{OK: true, Output: fmt.Sprintf("agent #%d: %s\nruntime: %.1fs\nlog:\n%s", id, status, info.Runtime(), c.Manager.GetOutput(id))}
			}
		}
		return Result{OK: true, Output: status}
	}
	items := c.Manager.List()
	if len(items) == 0 {
		return Result{OK: true, Output: "Tidak ada ghost agent."}
	}
	var lines []string
	for _, info := range items {
		lines = append(lines, fmt.Sprintf("#%d %s (%.1fs)", info.ID, info.Status, info.Runtime()))
	}
	return Result{OK: true, Output: strings.Join(lines, "\n")}
}
