package tool

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/autokeren/autokeren/internal/kanban"
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

type Kanban struct {
	Store *kanban.Store
}

func NewKanban(root string) *Kanban { return &Kanban{Store: kanban.New(root)} }
func (k *Kanban) Definition() Definition {
	return Definition{Name: "kanban", Description: "Kelola papan Kanban SQLite dan metadata manajemen proyek.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string", "enum": []string{"add", "move", "update", "delete", "list", "clear", "set_metadata", "get_metadata", "list_metadata"}}, "task_id": map[string]any{"type": "integer"}, "title": map[string]any{"type": "string"}, "description": map[string]any{"type": "string"}, "status": map[string]any{"type": "string", "enum": []string{"todo", "in_progress", "done"}}, "priority": map[string]any{"type": "string", "enum": []string{"low", "medium", "high"}}, "meta_key": map[string]any{"type": "string"}, "meta_value": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (k *Kanban) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (k *Kanban) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	action, _ := args["action"].(string)
	switch action {
	case "add":
		title, _ := args["title"].(string)
		description, _ := args["description"].(string)
		status, _ := args["status"].(string)
		priority, _ := args["priority"].(string)
		task, err := k.Store.Add(title, description, status, priority)
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		return Result{OK: true, Output: task}
	case "move", "update":
		id := taskID(args)
		update := kanban.Update{}
		if action == "move" {
			status, ok := args["status"].(string)
			if !ok || status == "" {
				return Result{OK: false, Error: "status wajib untuk move"}
			}
			update.Status = &status
		} else {
			if value, ok := args["title"].(string); ok {
				update.Title = &value
			}
			if value, ok := args["description"].(string); ok {
				update.Description = &value
			}
			if value, ok := args["status"].(string); ok {
				update.Status = &value
			}
			if value, ok := args["priority"].(string); ok {
				update.Priority = &value
			}
		}
		task, changed, err := k.Store.Update(id, update)
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		if !changed {
			return Result{OK: false, Error: "task tidak ditemukan"}
		}
		return Result{OK: true, Output: task}
	case "delete":
		deleted, err := k.Store.Delete(taskID(args))
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		if !deleted {
			return Result{OK: false, Error: "task tidak ditemukan"}
		}
		tasks, err := k.Store.List()
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		return Result{OK: true, Output: tasks}
	case "clear":
		if err := k.Store.Clear(); err != nil {
			return Result{OK: false, Error: err.Error()}
		}
	case "list":
		tasks, err := k.Store.List()
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		return Result{OK: true, Output: tasks}
	case "set_metadata":
		key, _ := args["meta_key"].(string)
		value, _ := args["meta_value"].(string)
		if strings.TrimSpace(value) == "" {
			return Result{OK: false, Error: "meta_value wajib diisi"}
		}
		if err := k.Store.SetMetadata(key, value); err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		return Result{OK: true, Output: "metadata tersimpan"}
	case "get_metadata":
		key, _ := args["meta_key"].(string)
		if strings.TrimSpace(key) == "" {
			return Result{OK: false, Error: "meta_key wajib diisi"}
		}
		value, err := k.Store.GetMetadata(key, "")
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		return Result{OK: true, Output: key + ": " + value}
	case "list_metadata":
		metadata, err := k.Store.Metadata()
		if err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		return Result{OK: true, Output: metadata}
	default:
		return Result{OK: false, Error: "action kanban tidak dikenal"}
	}
	tasks, err := k.Store.List()
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	return Result{OK: true, Output: tasks}
}

func taskID(args map[string]any) int {
	switch value := args["task_id"].(type) {
	case int:
		return value
	case int64:
		return int(value)
	case float64:
		return int(value)
	default:
		return 0
	}
}
