package kanban

import (
	"crypto/md5"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
	"unicode"

	_ "modernc.org/sqlite"
)

var validStatuses = map[string]struct{}{"todo": {}, "in_progress": {}, "done": {}}
var validPriorities = map[string]struct{}{"low": {}, "medium": {}, "high": {}}

type Task struct {
	ID          int    `json:"id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Status      string `json:"status"`
	Priority    string `json:"priority"`
	CreatedAt   string `json:"created_at"`
	UpdatedAt   string `json:"updated_at"`
}

type Update struct {
	Title       *string
	Description *string
	Status      *string
	Priority    *string
}

type Store struct {
	root         string
	primaryPath  string
	fallbackPath string
	legacyPath   string
	mu           sync.Mutex
	initialized  bool
	databasePath string
}

func New(root string) *Store {
	resolved := resolveRoot(root)
	projectDir := filepath.Join(configBase(), "projects", projectSlug(resolved))
	return &Store{
		root:         resolved,
		primaryPath:  filepath.Join(resolved, ".ak-kanban.db"),
		fallbackPath: filepath.Join(projectDir, "kanban.db"),
		legacyPath:   filepath.Join(resolved, ".autokeren", "kanban.json"),
	}
}

func (s *Store) Path() (string, error) {
	if err := s.ensure(); err != nil {
		return "", err
	}
	return s.databasePath, nil
}

func (s *Store) Add(title, description, status, priority string) (Task, error) {
	title = strings.TrimSpace(title)
	if title == "" {
		return Task{}, errors.New("title wajib untuk add")
	}
	if status == "" {
		status = "todo"
	}
	if priority == "" {
		priority = "medium"
	}
	if err := validateStatus(status); err != nil {
		return Task{}, err
	}
	if err := validatePriority(priority); err != nil {
		return Task{}, err
	}
	db, err := s.open()
	if err != nil {
		return Task{}, err
	}
	defer db.Close()
	result, err := db.Exec("INSERT INTO kanban_tasks (title, description, status, priority, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)", title, nullableString(description), status, priority)
	if err != nil {
		return Task{}, fmt.Errorf("tambah task kanban: %w", err)
	}
	id, err := result.LastInsertId()
	if err != nil {
		return Task{}, fmt.Errorf("ambil id task kanban: %w", err)
	}
	return taskByID(db, int(id))
}

func (s *Store) Update(id int, update Update) (Task, bool, error) {
	if id <= 0 {
		return Task{}, false, errors.New("task_id wajib bernilai lebih dari 0")
	}
	fields := make([]string, 0, 5)
	values := make([]any, 0, 5)
	if update.Title != nil {
		title := strings.TrimSpace(*update.Title)
		if title == "" {
			return Task{}, false, errors.New("title tidak boleh kosong")
		}
		fields = append(fields, "title = ?")
		values = append(values, title)
	}
	if update.Description != nil {
		fields = append(fields, "description = ?")
		values = append(values, nullableString(*update.Description))
	}
	if update.Status != nil {
		if err := validateStatus(*update.Status); err != nil {
			return Task{}, false, err
		}
		fields = append(fields, "status = ?")
		values = append(values, *update.Status)
	}
	if update.Priority != nil {
		if err := validatePriority(*update.Priority); err != nil {
			return Task{}, false, err
		}
		fields = append(fields, "priority = ?")
		values = append(values, *update.Priority)
	}
	if len(fields) == 0 {
		return Task{}, false, errors.New("tidak ada field task untuk diperbarui")
	}
	fields = append(fields, "updated_at = CURRENT_TIMESTAMP")
	values = append(values, id)
	db, err := s.open()
	if err != nil {
		return Task{}, false, err
	}
	defer db.Close()
	result, err := db.Exec("UPDATE kanban_tasks SET "+strings.Join(fields, ", ")+" WHERE id = ?", values...)
	if err != nil {
		return Task{}, false, fmt.Errorf("perbarui task kanban: %w", err)
	}
	changed, err := result.RowsAffected()
	if err != nil {
		return Task{}, false, err
	}
	if changed == 0 {
		return Task{}, false, nil
	}
	task, err := taskByID(db, id)
	return task, true, err
}

func (s *Store) Delete(id int) (bool, error) {
	if id <= 0 {
		return false, errors.New("task_id wajib bernilai lebih dari 0")
	}
	db, err := s.open()
	if err != nil {
		return false, err
	}
	defer db.Close()
	result, err := db.Exec("DELETE FROM kanban_tasks WHERE id = ?", id)
	if err != nil {
		return false, fmt.Errorf("hapus task kanban: %w", err)
	}
	changed, err := result.RowsAffected()
	return changed > 0, err
}

func (s *Store) Clear() error {
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec("DELETE FROM kanban_tasks")
	if err != nil {
		return fmt.Errorf("bersihkan task kanban: %w", err)
	}
	return nil
}

func (s *Store) List() ([]Task, error) {
	db, err := s.open()
	if err != nil {
		return nil, err
	}
	defer db.Close()
	rows, err := db.Query("SELECT id, title, description, status, priority, created_at, updated_at FROM kanban_tasks ORDER BY id ASC")
	if err != nil {
		return nil, fmt.Errorf("daftar task kanban: %w", err)
	}
	defer rows.Close()
	tasks := make([]Task, 0)
	for rows.Next() {
		task, err := scanTask(rows)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, rows.Err()
}

func (s *Store) SetMetadata(key, value string) error {
	key = strings.TrimSpace(key)
	if key == "" {
		return errors.New("meta_key wajib diisi")
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec("INSERT INTO project_metadata (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", key, value)
	if err != nil {
		return fmt.Errorf("simpan metadata kanban: %w", err)
	}
	return nil
}

func (s *Store) GetMetadata(key, fallback string) (string, error) {
	db, err := s.open()
	if err != nil {
		return "", err
	}
	defer db.Close()
	var value string
	err = db.QueryRow("SELECT value FROM project_metadata WHERE key = ?", key).Scan(&value)
	if errors.Is(err, sql.ErrNoRows) {
		return fallback, nil
	}
	if err != nil {
		return "", fmt.Errorf("baca metadata kanban: %w", err)
	}
	return value, nil
}

func (s *Store) Metadata() (map[string]string, error) {
	db, err := s.open()
	if err != nil {
		return nil, err
	}
	defer db.Close()
	rows, err := db.Query("SELECT key, value FROM project_metadata")
	if err != nil {
		return nil, fmt.Errorf("daftar metadata kanban: %w", err)
	}
	defer rows.Close()
	metadata := map[string]string{}
	for rows.Next() {
		var key, value string
		if err := rows.Scan(&key, &value); err != nil {
			return nil, err
		}
		metadata[key] = value
	}
	return metadata, rows.Err()
}

func (s *Store) open() (*sql.DB, error) {
	if err := s.ensure(); err != nil {
		return nil, err
	}
	db, err := sql.Open("sqlite", s.databasePath)
	if err != nil {
		return nil, fmt.Errorf("buka database kanban: %w", err)
	}
	if _, err := db.Exec("PRAGMA busy_timeout = 5000"); err != nil {
		db.Close()
		return nil, fmt.Errorf("atur database kanban: %w", err)
	}
	return db, nil
}

func (s *Store) ensure() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.initialized {
		return nil
	}
	path, err := initializeDatabase(s.primaryPath)
	if err != nil {
		path, err = initializeDatabase(s.fallbackPath)
		if err != nil {
			return fmt.Errorf("inisialisasi kanban di project dan config fallback: %w", err)
		}
	}
	s.databasePath = path
	if err := s.migrateLegacyLocked(); err != nil {
		return err
	}
	if err := s.seedMetadataLocked(); err != nil {
		return err
	}
	s.initialized = true
	return nil
}

func initializeDatabase(path string) (string, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return "", err
	}
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return "", err
	}
	defer db.Close()
	if _, err := db.Exec("PRAGMA busy_timeout = 5000"); err != nil {
		return "", err
	}
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS kanban_tasks (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		description TEXT,
		status TEXT CHECK(status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo',
		priority TEXT CHECK(priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)`); err != nil {
		return "", err
	}
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS project_metadata (
		key TEXT PRIMARY KEY,
		value TEXT
	)`); err != nil {
		return "", err
	}
	return path, nil
}

func (s *Store) migrateLegacyLocked() error {
	data, err := os.ReadFile(filepath.Clean(s.legacyPath))
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("baca kanban JSON Go lama: %w", err)
	}
	db, err := sql.Open("sqlite", s.databasePath)
	if err != nil {
		return err
	}
	defer db.Close()
	var marker string
	err = db.QueryRow("SELECT value FROM project_metadata WHERE key = ?", "go_json_migration_v1").Scan(&marker)
	if err == nil {
		return nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return err
	}
	var tasks []Task
	if err := json.Unmarshal(data, &tasks); err != nil {
		return fmt.Errorf("kanban JSON Go lama tidak valid: %w", err)
	}
	backup := s.legacyPath + ".bak-" + time.Now().UTC().Format("20060102-150405")
	if err := writeFileAtomic(backup, data); err != nil {
		return fmt.Errorf("backup kanban JSON Go lama: %w", err)
	}
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	for _, task := range tasks {
		if task.ID <= 0 || strings.TrimSpace(task.Title) == "" {
			return fmt.Errorf("task legacy tidak valid dengan id %d", task.ID)
		}
		if task.Status == "" {
			task.Status = "todo"
		}
		if task.Priority == "" {
			task.Priority = "medium"
		}
		if err := validateStatus(task.Status); err != nil {
			return fmt.Errorf("task legacy #%d: %w", task.ID, err)
		}
		if err := validatePriority(task.Priority); err != nil {
			return fmt.Errorf("task legacy #%d: %w", task.ID, err)
		}
		var existingTitle string
		err := tx.QueryRow("SELECT title FROM kanban_tasks WHERE id = ?", task.ID).Scan(&existingTitle)
		if err == nil {
			return fmt.Errorf("konflik migrasi task legacy #%d dengan SQLite", task.ID)
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return err
		}
		if _, err := tx.Exec("INSERT INTO kanban_tasks (id, title, description, status, priority) VALUES (?, ?, ?, ?, ?)", task.ID, task.Title, nullableString(task.Description), task.Status, task.Priority); err != nil {
			return fmt.Errorf("migrasi task legacy #%d: %w", task.ID, err)
		}
	}
	if _, err := tx.Exec("INSERT INTO project_metadata (key, value) VALUES (?, ?)", "go_json_migration_v1", "completed"); err != nil {
		return err
	}
	return tx.Commit()
}

func (s *Store) seedMetadataLocked() error {
	db, err := sql.Open("sqlite", s.databasePath)
	if err != nil {
		return err
	}
	defer db.Close()
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM project_metadata WHERE key != ?", "go_json_migration_v1").Scan(&count); err != nil {
		return err
	}
	if count > 0 {
		return nil
	}
	name := filepath.Base(s.root)
	if name == "" || name == string(filepath.Separator) || name == "." {
		name = "default"
	}
	stack := detectStack(s.root)
	metadata := map[string]string{
		"project_name":    name,
		"project_path":    s.root,
		"tech_stack":      stack,
		"frontend_link":   "http://localhost:3000",
		"backend_link":    "http://localhost:8787",
		"runbook_install": "npm install",
		"runbook_run":     "npm run dev",
		"runbook_test":    "npm test",
	}
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	for key, value := range metadata {
		if _, err := tx.Exec("INSERT INTO project_metadata (key, value) VALUES (?, ?)", key, value); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func taskByID(db *sql.DB, id int) (Task, error) {
	return scanTask(db.QueryRow("SELECT id, title, description, status, priority, created_at, updated_at FROM kanban_tasks WHERE id = ?", id))
}

type scanner interface {
	Scan(dest ...any) error
}

func scanTask(row scanner) (Task, error) {
	var task Task
	var description sql.NullString
	if err := row.Scan(&task.ID, &task.Title, &description, &task.Status, &task.Priority, &task.CreatedAt, &task.UpdatedAt); err != nil {
		return Task{}, err
	}
	task.Description = description.String
	return task, nil
}

func validateStatus(status string) error {
	if _, ok := validStatuses[status]; !ok {
		return fmt.Errorf("status kanban tidak valid: %s", status)
	}
	return nil
}

func validatePriority(priority string) error {
	if _, ok := validPriorities[priority]; !ok {
		return fmt.Errorf("priority kanban tidak valid: %s", priority)
	}
	return nil
}

func nullableString(value string) any {
	if value == "" {
		return nil
	}
	return value
}

func resolveRoot(root string) string {
	resolved, err := filepath.Abs(root)
	if err != nil {
		resolved = root
	}
	if realPath, err := filepath.EvalSymlinks(resolved); err == nil {
		return realPath
	}
	return filepath.Clean(resolved)
}

func configBase() string {
	if base := strings.TrimSpace(os.Getenv("AUTOKEREN_CONFIG_DIR")); base != "" {
		return base
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return filepath.Join(".", ".config", "autokeren")
	}
	return filepath.Join(home, ".config", "autokeren")
}

func projectSlug(root string) string {
	name := strings.Trim(strings.Map(func(r rune) rune {
		if unicode.IsLetter(r) || unicode.IsNumber(r) || r == '_' || r == '-' || r == '.' {
			return r
		}
		return '_'
	}, filepath.Base(root)), "._")
	if name == "" {
		name = "default"
	}
	sum := md5.Sum([]byte(root))
	return name + "-" + hex.EncodeToString(sum[:])[:8]
}

func detectStack(root string) string {
	stacks := make([]string, 0, 5)
	if fileExists(filepath.Join(root, "package.json")) {
		stacks = append(stacks, "Node.js")
	}
	if fileExists(filepath.Join(root, "requirements.txt")) || fileExists(filepath.Join(root, "pyproject.toml")) || fileExists(filepath.Join(root, "setup.py")) {
		stacks = append(stacks, "Python")
	}
	if fileExists(filepath.Join(root, "go.mod")) {
		stacks = append(stacks, "Go")
	}
	if fileExists(filepath.Join(root, "Cargo.toml")) {
		stacks = append(stacks, "Rust")
	}
	if fileExists(filepath.Join(root, "wrangler.toml")) || fileExists(filepath.Join(root, "wrangler.json")) {
		stacks = append(stacks, "Cloudflare Workers")
	}
	if len(stacks) == 0 {
		return "Unknown"
	}
	return strings.Join(stacks, ", ")
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func writeFileAtomic(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	file, err := os.CreateTemp(filepath.Dir(path), ".kanban-*")
	if err != nil {
		return err
	}
	temporary := file.Name()
	defer os.Remove(temporary)
	if err := file.Chmod(0o600); err != nil {
		file.Close()
		return err
	}
	if _, err := file.Write(data); err != nil {
		file.Close()
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	return os.Rename(temporary, path)
}
