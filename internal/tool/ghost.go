package tool

import (
	"context"
	"fmt"
	"github.com/autokeren/autokeren/ghost"
)

type SpawnGhost struct{ Manager *ghost.GhostManager }

func (s SpawnGhost) Definition() Definition {
	return Definition{Name: "spawn_agent", Description: "Spawn a native Go background ghost agent.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"task": map[string]any{"type": "string"}}, "required": []string{"task"}}}
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
	info, err := s.Manager.Spawn(task)
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
		return Result{OK: true, Output: c.Manager.CheckStatus(int(v))}
	}
	return Result{OK: true, Output: c.Manager.List()}
}
