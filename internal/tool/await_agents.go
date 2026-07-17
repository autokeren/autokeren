package tool

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/autokeren/autokeren/internal/director"
)

type AwaitAgents struct{ Coordinator *director.Coordinator }

func (a AwaitAgents) Definition() Definition {
	return Definition{Name: "await_agents", Description: "Wait for delegated Go agents, collect bounded results into the director mailbox, then return their evidence to the director.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"agent_ids": map[string]any{"type": "array", "items": map[string]any{"type": "integer"}}, "timeout_seconds": map[string]any{"type": "integer", "minimum": 1, "maximum": 600}}, "required": []string{"agent_ids"}}}
}

func (a AwaitAgents) NeedsPermission(map[string]any) (bool, string) { return false, "" }

func (a AwaitAgents) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	if a.Coordinator == nil {
		return Result{OK: false, Error: "director mailbox tidak tersedia"}
	}
	ids, err := agentIDs(args["agent_ids"])
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	timeout := 5 * time.Minute
	if seconds, ok := args["timeout_seconds"].(float64); ok && seconds > 0 {
		timeout = time.Duration(seconds) * time.Second
	}
	mailbox, err := a.Coordinator.Await(ctx, ids, timeout)
	data, _ := json.Marshal(mailbox)
	if err != nil {
		return Result{OK: false, Output: string(data), Error: err.Error()}
	}
	return Result{OK: true, Output: string(data)}
}

func agentIDs(value any) ([]int, error) {
	raw, ok := value.([]any)
	if !ok || len(raw) == 0 {
		return nil, fmt.Errorf("agent_ids wajib berupa daftar ID agent")
	}
	ids := make([]int, 0, len(raw))
	seen := map[int]struct{}{}
	for _, item := range raw {
		parsed, ok := item.(float64)
		if !ok || parsed <= 0 || parsed != float64(int(parsed)) {
			return nil, fmt.Errorf("agent_ids harus berisi integer positif")
		}
		id := int(parsed)
		if _, exists := seen[id]; exists {
			continue
		}
		seen[id] = struct{}{}
		ids = append(ids, id)
	}
	return ids, nil
}
