package session

import (
	"crypto/md5"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/autokeren/autokeren/internal/model"
	_ "modernc.org/sqlite"
)

var safeName = regexp.MustCompile(`[^\w\-_.]`)

type Manager struct {
	dbPath      string
	projectRoot string
}

type Summary struct {
	ID        string
	Name      string
	Timestamp string
	Messages  int
}

func NewManager(projectRoot string) (*Manager, error) {
	base := os.Getenv("AUTOKEREN_CONFIG_DIR")
	if base == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return nil, fmt.Errorf("temukan home directory: %w", err)
		}
		base = filepath.Join(home, ".config", "autokeren")
	}
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return nil, fmt.Errorf("resolve project root: %w", err)
	}
	if resolved, resolveErr := filepath.EvalSymlinks(root); resolveErr == nil {
		root = resolved
	}
	name := strings.Trim(safeName.ReplaceAllString(filepath.Base(root), "_"), "._")
	if name == "" {
		name = "default"
	}
	sum := md5.Sum([]byte(root))
	slug := name + "-" + hex.EncodeToString(sum[:])[:8]
	dir := filepath.Join(base, "projects", slug, "sessions")
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return nil, fmt.Errorf("buat direktori session: %w", err)
	}
	manager := &Manager{dbPath: filepath.Join(dir, "sessions.db"), projectRoot: root}
	if err := manager.initialize(); err != nil {
		return nil, err
	}
	return manager, nil
}

func (m *Manager) Path() string {
	return m.dbPath
}

func (m *Manager) initialize() error {
	db, err := m.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS sessions (
		id TEXT PRIMARY KEY,
		name TEXT NOT NULL,
		project TEXT NOT NULL,
		timestamp TEXT NOT NULL,
		messages TEXT NOT NULL,
		usage TEXT NOT NULL
	)`)
	if err != nil {
		return fmt.Errorf("inisialisasi database session: %w", err)
	}
	return nil
}

func (m *Manager) open() (*sql.DB, error) {
	db, err := sql.Open("sqlite", m.dbPath)
	if err != nil {
		return nil, fmt.Errorf("buka database session: %w", err)
	}
	if _, err := db.Exec("PRAGMA busy_timeout = 5000"); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func (m *Manager) Save(name string, messages []model.Message, usage model.Usage, sessionID string) (Data, error) {
	if strings.TrimSpace(name) == "" {
		return Data{}, errors.New("nama session kosong")
	}
	messagesJSON, err := json.Marshal(messages)
	if err != nil {
		return Data{}, fmt.Errorf("serialisasi pesan session: %w", err)
	}
	usageJSON, err := json.Marshal(usage)
	if err != nil {
		return Data{}, fmt.Errorf("serialisasi penggunaan session: %w", err)
	}
	now := time.Now().UTC()
	timestamp := now.Format(time.RFC3339Nano)
	db, err := m.open()
	if err != nil {
		return Data{}, err
	}
	defer db.Close()
	if sessionID != "" {
		result, updateErr := db.Exec("UPDATE sessions SET name = ?, timestamp = ?, messages = ?, usage = ? WHERE id = ?", name, timestamp, string(messagesJSON), string(usageJSON), sessionID)
		if updateErr != nil {
			return Data{}, fmt.Errorf("update session: %w", updateErr)
		}
		if count, countErr := result.RowsAffected(); countErr == nil && count > 0 {
			return Data{ID: sessionID, Name: name, CreatedAt: now, UpdatedAt: now, Messages: messages, Usage: usage}, nil
		}
	}
	id, err := nextID(db)
	if err != nil {
		return Data{}, err
	}
	if _, err := db.Exec("INSERT INTO sessions (id, name, project, timestamp, messages, usage) VALUES (?, ?, ?, ?, ?, ?)", id, name, m.projectRoot, timestamp, string(messagesJSON), string(usageJSON)); err != nil {
		return Data{}, fmt.Errorf("simpan session: %w", err)
	}
	return Data{ID: id, Name: name, CreatedAt: now, UpdatedAt: now, Messages: messages, Usage: usage}, nil
}

func nextID(db *sql.DB) (string, error) {
	base := time.Now().UTC().Format("20060102150405")
	id := base
	for counter := 1; ; counter++ {
		var found int
		err := db.QueryRow("SELECT 1 FROM sessions WHERE id = ?", id).Scan(&found)
		if errors.Is(err, sql.ErrNoRows) {
			return id, nil
		}
		if err != nil {
			return "", fmt.Errorf("cek session id: %w", err)
		}
		id = fmt.Sprintf("%s-%d", base, counter)
	}
}

func (m *Manager) Load(identifier string) (Data, error) {
	identifier = strings.TrimSpace(identifier)
	if identifier == "" {
		return Data{}, errors.New("identifier session kosong")
	}
	db, err := m.open()
	if err != nil {
		return Data{}, err
	}
	defer db.Close()
	query := "SELECT id, name, timestamp, messages, usage FROM sessions WHERE lower(id) = ? OR lower(name) = ? ORDER BY timestamp DESC LIMIT 1"
	data, err := loadRow(db.QueryRow(query, strings.ToLower(identifier), strings.ToLower(identifier)))
	if err == nil {
		return data, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return Data{}, err
	}
	query = "SELECT id, name, timestamp, messages, usage FROM sessions WHERE lower(id) LIKE ? OR lower(name) LIKE ? ORDER BY timestamp DESC LIMIT 1"
	return loadRow(db.QueryRow(query, "%"+strings.ToLower(identifier)+"%", "%"+strings.ToLower(identifier)+"%"))
}

func (m *Manager) List() ([]Summary, error) {
	db, err := m.open()
	if err != nil {
		return nil, err
	}
	defer db.Close()
	rows, err := db.Query("SELECT id, name, timestamp, messages FROM sessions ORDER BY timestamp DESC")
	if err != nil {
		return nil, fmt.Errorf("daftar session: %w", err)
	}
	defer rows.Close()
	items := make([]Summary, 0)
	for rows.Next() {
		var item Summary
		var messagesJSON string
		if err := rows.Scan(&item.ID, &item.Name, &item.Timestamp, &messagesJSON); err != nil {
			return nil, err
		}
		messages, messageErr := decodeMessages([]byte(messagesJSON))
		if messageErr == nil {
			item.Messages = len(messages)
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

type rowScanner interface {
	Scan(dest ...any) error
}

func loadRow(row rowScanner) (Data, error) {
	var data Data
	var timestamp string
	var messagesJSON string
	var usageJSON string
	if err := row.Scan(&data.ID, &data.Name, &timestamp, &messagesJSON, &usageJSON); err != nil {
		return Data{}, err
	}
	parsed, err := time.Parse(time.RFC3339Nano, timestamp)
	if err == nil {
		data.CreatedAt = parsed
		data.UpdatedAt = parsed
	}
	data.Messages, err = decodeMessages([]byte(messagesJSON))
	if err != nil {
		return Data{}, fmt.Errorf("baca pesan session: %w", err)
	}
	if err := json.Unmarshal([]byte(usageJSON), &data.Usage); err != nil {
		return Data{}, fmt.Errorf("baca penggunaan session: %w", err)
	}
	return data, nil
}

func decodeMessages(raw []byte) ([]model.Message, error) {
	var messages []model.Message
	if err := json.Unmarshal(raw, &messages); err == nil {
		return messages, nil
	}
	var rawMessages []map[string]json.RawMessage
	if err := json.Unmarshal(raw, &rawMessages); err != nil {
		return nil, err
	}
	messages = make([]model.Message, 0, len(rawMessages))
	for _, rawMessage := range rawMessages {
		var message model.Message
		if role, ok := rawMessage["role"]; ok {
			_ = json.Unmarshal(role, &message.Role)
		}
		if name, ok := rawMessage["name"]; ok {
			_ = json.Unmarshal(name, &message.Name)
		}
		if toolCallID, ok := rawMessage["tool_call_id"]; ok {
			_ = json.Unmarshal(toolCallID, &message.ToolCallID)
		}
		if content, ok := rawMessage["content"]; ok {
			if err := json.Unmarshal(content, &message.Content); err != nil {
				message.Content = flattenContent(content)
			}
		}
		if calls, ok := rawMessage["tool_calls"]; ok {
			_ = json.Unmarshal(calls, &message.ToolCalls)
		}
		messages = append(messages, message)
	}
	return messages, nil
}

func flattenContent(raw json.RawMessage) string {
	var parts []struct {
		Text string `json:"text"`
	}
	if json.Unmarshal(raw, &parts) == nil {
		text := make([]string, 0, len(parts))
		for _, part := range parts {
			if part.Text != "" {
				text = append(text, part.Text)
			}
		}
		return strings.Join(text, " ")
	}
	return string(raw)
}
