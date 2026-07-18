package tool

import (
	"context"
	"fmt"
	"github.com/autokeren/autokeren/ghost"
	"strings"
)

type SpawnGhost struct{ Manager *ghost.GhostManager }

func (s SpawnGhost) Definition() Definition {
	return Definition{Name: "spawn_agent", Description: "Spawn a native Go sub-agent. Workers are read-only unless allowed_tools explicitly grants a known mutable capability.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"task": map[string]any{"type": "string"}, "context": map[string]any{"type": "string"}, "role": map[string]any{"type": "string"}, "model_id": map[string]any{"type": "string"}, "background": map[string]any{"type": "boolean"}, "agent_name": map[string]any{"type": "string"}, "allowed_tools": map[string]any{"type": "array", "items": map[string]any{"type": "string"}}}, "required": []string{"task"}}}
}
func (s SpawnGhost) NeedsPermission(args map[string]any) (bool, string) {
	allowed := parseAllowedTools(args["allowed_tools"])
	if len(allowed) == 0 {
		return true, "spawn native Go ghost agent (read-only)"
	}
	return true, "spawn native Go ghost agent dengan capability: " + strings.Join(allowed, ", ")
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
	options.AllowedTools = parseAllowedTools(args["allowed_tools"])
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

func parseAllowedTools(value any) []string {
	raw, ok := value.([]any)
	if !ok {
		return nil
	}
	values := make([]string, 0, len(raw))
	for _, item := range raw {
		if name, ok := item.(string); ok {
			values = append(values, name)
		}
	}
	return ghost.AllowedTools(values)
}

type CheckGhost struct{ Manager *ghost.GhostManager }

type StopGhost struct{ Manager *ghost.GhostManager }

func (s StopGhost) Definition() Definition {
	return Definition{Name: "stop_agent", Description: "Stop a running native Go worker after a timeout or when its work is no longer needed.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"agent_id": map[string]any{"type": "integer"}}, "required": []string{"agent_id"}}}
}

func (s StopGhost) NeedsPermission(args map[string]any) (bool, string) {
	return true, fmt.Sprintf("hentikan agent #%v", args["agent_id"])
}

func (s StopGhost) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	id, ok := args["agent_id"].(float64)
	if !ok || id <= 0 || id != float64(int(id)) {
		return Result{OK: false, Error: "agent_id harus integer positif"}
	}
	if !s.Manager.Kill(int(id)) {
		return Result{OK: false, Error: "agent tidak sedang berjalan atau tidak ditemukan"}
	}
	return Result{OK: true, Output: fmt.Sprintf("agent #%d dihentikan", int(id))}
}

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
