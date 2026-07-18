package kanban

import (
	"database/sql"
	"os"
	"path/filepath"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

func TestStoreReadsPythonBoardAndWritesCompatibleRows(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, ".ak-kanban.db")
	db, err := sql.Open("sqlite", path)
	if err != nil {
		t.Fatal(err)
	}
	_, err = db.Exec(`CREATE TABLE kanban_tasks (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		description TEXT,
		status TEXT CHECK(status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo',
		priority TEXT CHECK(priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	); CREATE TABLE project_metadata (key TEXT PRIMARY KEY, value TEXT);`)
	if err != nil {
		db.Close()
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO kanban_tasks (title, description, status, priority) VALUES (?, ?, ?, ?)", "Task Python", "dibuat runtime Python", "todo", "high"); err != nil {
		db.Close()
		t.Fatal(err)
	}
	db.Close()
	store := New(root)
	tasks, err := store.List()
	if err != nil || len(tasks) != 1 || tasks[0].Title != "Task Python" || tasks[0].Description != "dibuat runtime Python" {
		t.Fatalf("board Python tidak terbaca: %#v err=%v", tasks, err)
	}
	status := "in_progress"
	updated, changed, err := store.Update(tasks[0].ID, Update{Status: &status})
	if err != nil || !changed || updated.Status != status {
		t.Fatalf("update Go gagal: %#v changed=%v err=%v", updated, changed, err)
	}
	created, err := store.Add("Task Go", "ditulis runtime Go", "done", "low")
	if err != nil || created.ID != 2 {
		t.Fatalf("insert Go gagal: %#v err=%v", created, err)
	}
	db, err = sql.Open("sqlite", path)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	var title, movedStatus string
	if err := db.QueryRow("SELECT title, status FROM kanban_tasks WHERE id = ?", tasks[0].ID).Scan(&title, &movedStatus); err != nil || title != "Task Python" || movedStatus != "in_progress" {
		t.Fatalf("baris Go tidak kompatibel untuk Python: title=%q status=%q err=%v", title, movedStatus, err)
	}
}

func TestStoreMigratesLegacyJSONSafelyAndOnce(t *testing.T) {
	root := t.TempDir()
	legacyPath := filepath.Join(root, ".autokeren", "kanban.json")
	legacy := "[\n  {\"id\": 7, \"title\": \"Task legacy\", \"description\": \"jangan hilang\", \"status\": \"todo\", \"priority\": \"high\"}\n]\n"
	if err := os.MkdirAll(filepath.Dir(legacyPath), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(legacyPath, []byte(legacy), 0o600); err != nil {
		t.Fatal(err)
	}
	store := New(root)
	tasks, err := store.List()
	if err != nil || len(tasks) != 1 || tasks[0].ID != 7 || tasks[0].Title != "Task legacy" {
		t.Fatalf("migrasi JSON gagal: %#v err=%v", tasks, err)
	}
	backups, err := filepath.Glob(legacyPath + ".bak-*")
	if err != nil || len(backups) != 1 {
		t.Fatalf("backup legacy tidak dibuat: %#v err=%v", backups, err)
	}
	for _, path := range append(backups, legacyPath) {
		data, readErr := os.ReadFile(path)
		if readErr != nil || string(data) != legacy {
			t.Fatalf("data legacy berubah untuk %s: %q %v", path, data, readErr)
		}
	}
	tasks, err = store.List()
	if err != nil || len(tasks) != 1 || tasks[0].ID != 7 {
		t.Fatalf("migrasi kedua tidak idempotent: %#v err=%v", tasks, err)
	}
}

func TestStoreInvalidMutationLeavesBoardIntact(t *testing.T) {
	store := New(t.TempDir())
	task, err := store.Add("Task valid", "", "todo", "medium")
	if err != nil {
		t.Fatal(err)
	}
	invalid := "broken"
	if _, changed, err := store.Update(task.ID, Update{Status: &invalid}); err == nil || changed {
		t.Fatalf("status invalid harus ditolak: changed=%v err=%v", changed, err)
	}
	if deleted, err := store.Delete(999); err != nil || deleted {
		t.Fatalf("delete task tidak ada harus jujur: deleted=%v err=%v", deleted, err)
	}
	tasks, err := store.List()
	if err != nil || len(tasks) != 1 || tasks[0].Status != "todo" {
		t.Fatalf("board berubah setelah error: %#v err=%v", tasks, err)
	}
}

func TestStoreSeedsPythonMetadataAfterLegacyMigration(t *testing.T) {
	root := t.TempDir()
	legacyPath := filepath.Join(root, ".autokeren", "kanban.json")
	if err := os.MkdirAll(filepath.Dir(legacyPath), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(legacyPath, []byte("[]"), 0o600); err != nil {
		t.Fatal(err)
	}
	metadata, err := New(root).Metadata()
	if err != nil || metadata["project_name"] == "" || metadata["tech_stack"] == "" {
		t.Fatalf("metadata Python tidak terseed: %#v err=%v", metadata, err)
	}
	if !strings.Contains(metadata["project_path"], root) {
		t.Fatalf("metadata project_path tidak kompatibel: %#v", metadata)
	}
}
