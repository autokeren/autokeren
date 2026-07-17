package tool

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
)

type Todo struct {
	Content string `json:"content"`
	Status  string `json:"status"`
}
type TodoList struct {
	Root  string
	mu    sync.Mutex
	Items []Todo
}

func NewTodoList(root string) *TodoList { return &TodoList{Root: root} }
func (t *TodoList) Definition() Definition {
	return Definition{Name: "todo", Description: "Manage a persistent todo list.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"add", "update", "list", "clear"}}, "content": map[string]any{"type": "string"}, "index": map[string]any{"type": "integer"}, "status": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (t *TodoList) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (t *TodoList) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	_ = t.load()
	action, _ := args["action"].(string)
	switch action {
	case "add":
		content, _ := args["content"].(string)
		if content == "" {
			return Result{OK: false, Error: "content wajib untuk add"}
		}
		t.Items = append(t.Items, Todo{Content: content, Status: "pending"})
	case "update":
		index, _ := args["index"].(float64)
		status, _ := args["status"].(string)
		i := int(index) - 1
		if i < 0 || i >= len(t.Items) {
			return Result{OK: false, Error: "index todo tidak valid"}
		}
		if status == "" {
			status = "pending"
		}
		t.Items[i].Status = status
	case "clear":
		t.Items = nil
	case "list":
	default:
		return Result{OK: false, Error: "action todo tidak dikenal"}
	}
	if action != "list" {
		if err := t.save(); err != nil {
			return Result{OK: false, Error: err.Error()}
		}
	}
	return Result{OK: true, Output: t.format()}
}
func (t *TodoList) format() string {
	if len(t.Items) == 0 {
		return "todo list kosong"
	}
	out := ""
	for i, item := range t.Items {
		icon := "○"
		if item.Status == "in_progress" {
			icon = "◐"
		}
		if item.Status == "completed" {
			icon = "●"
		}
		out += fmt.Sprintf("%d. %s %s [%s]\\n", i+1, icon, item.Content, item.Status)
	}
	return out
}
func (t *TodoList) path() string { return filepath.Join(t.Root, ".autokeren", "todos.json") }
func (t *TodoList) load() error {
	data, err := os.ReadFile(t.path())
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	return json.Unmarshal(data, &t.Items)
}
func (t *TodoList) save() error {
	if err := os.MkdirAll(filepath.Dir(t.path()), 0o700); err != nil {
		return err
	}
	data, _ := json.MarshalIndent(t.Items, "", "  ")
	return os.WriteFile(t.path(), data, 0o600)
}

type KanbanTask struct {
	ID          int    `json:"id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Status      string `json:"status"`
	Priority    string `json:"priority"`
}
type Kanban struct {
	Root   string
	mu     sync.Mutex
	Tasks  []KanbanTask
	NextID int
}

func NewKanban(root string) *Kanban { return &Kanban{Root: root, NextID: 1} }
func (k *Kanban) Definition() Definition {
	return Definition{Name: "kanban", Description: "Manage project Kanban tasks.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string"}, "task_id": map[string]any{"type": "integer"}, "title": map[string]any{"type": "string"}, "description": map[string]any{"type": "string"}, "status": map[string]any{"type": "string"}, "priority": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (k *Kanban) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (k *Kanban) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	k.mu.Lock()
	defer k.mu.Unlock()
	_ = k.load()
	action, _ := args["action"].(string)
	idv, _ := args["task_id"].(float64)
	id := int(idv)
	switch action {
	case "add":
		title, _ := args["title"].(string)
		if title == "" {
			return Result{OK: false, Error: "title wajib"}
		}
		status, _ := args["status"].(string)
		if status == "" {
			status = "todo"
		}
		priority, _ := args["priority"].(string)
		if priority == "" {
			priority = "medium"
		}
		k.Tasks = append(k.Tasks, KanbanTask{ID: k.NextID, Title: title, Status: status, Priority: priority})
		k.NextID++
	case "move", "update":
		for i := range k.Tasks {
			if k.Tasks[i].ID == id {
				if v, ok := args["status"].(string); ok && v != "" {
					k.Tasks[i].Status = v
				}
				if v, ok := args["title"].(string); ok && v != "" {
					k.Tasks[i].Title = v
				}
				if v, ok := args["description"].(string); ok {
					k.Tasks[i].Description = v
				}
				if v, ok := args["priority"].(string); ok && v != "" {
					k.Tasks[i].Priority = v
				}
				if err := k.save(); err != nil {
					return Result{OK: false, Error: err.Error()}
				}
				return Result{OK: true, Output: k.Tasks[i]}
			}
		}
		return Result{OK: false, Error: "task not found"}
	case "delete":
		for i := range k.Tasks {
			if k.Tasks[i].ID == id {
				k.Tasks = append(k.Tasks[:i], k.Tasks[i+1:]...)
				break
			}
		}
	case "clear":
		k.Tasks = nil
	case "list":
	default:
		return Result{OK: false, Error: "action kanban tidak dikenal"}
	}
	if action != "list" {
		if err := k.save(); err != nil {
			return Result{OK: false, Error: err.Error()}
		}
	}
	return Result{OK: true, Output: k.Tasks}
}
func (k *Kanban) path() string { return filepath.Join(k.Root, ".autokeren", "kanban.json") }
func (k *Kanban) load() error {
	data, err := os.ReadFile(k.path())
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	if err = json.Unmarshal(data, &k.Tasks); err == nil {
		for _, v := range k.Tasks {
			if v.ID >= k.NextID {
				k.NextID = v.ID + 1
			}
		}
	}
	return err
}
func (k *Kanban) save() error {
	if err := os.MkdirAll(filepath.Dir(k.path()), 0o700); err != nil {
		return err
	}
	data, _ := json.MarshalIndent(k.Tasks, "", "  ")
	return os.WriteFile(k.path(), data, 0o600)
}
