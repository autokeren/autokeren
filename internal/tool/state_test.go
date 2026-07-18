package tool

import (
	"context"
	"testing"

	"github.com/autokeren/autokeren/internal/kanban"
)

func TestKanbanToolUsesSQLiteCompatibleStore(t *testing.T) {
	board := NewKanban(t.TempDir())
	added := board.Run(context.Background(), map[string]any{
		"action":      "add",
		"title":       "Migrasikan Kanban",
		"description": "jaga kompatibilitas Python",
		"status":      "todo",
		"priority":    "high",
	}, nil)
	if !added.OK {
		t.Fatal(added.Error)
	}
	moved := board.Run(context.Background(), map[string]any{"action": "move", "task_id": float64(1), "status": "in_progress"}, nil)
	if !moved.OK {
		t.Fatal(moved.Error)
	}
	listed := board.Run(context.Background(), map[string]any{"action": "list"}, nil)
	if !listed.OK {
		t.Fatal(listed.Error)
	}
	tasks, ok := listed.Output.([]kanban.Task)
	if !ok || len(tasks) != 1 || tasks[0].Status != "in_progress" {
		t.Fatalf("task kanban tidak benar: %#v", listed.Output)
	}
	invalid := board.Run(context.Background(), map[string]any{"action": "move", "task_id": float64(1), "status": "broken"}, nil)
	if invalid.OK {
		t.Fatal("status invalid harus ditolak")
	}
	deleted := board.Run(context.Background(), map[string]any{"action": "delete", "task_id": float64(1)}, nil)
	if !deleted.OK {
		t.Fatal(deleted.Error)
	}
}
