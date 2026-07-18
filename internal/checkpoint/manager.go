package checkpoint

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
	"unicode"

	"github.com/autokeren/autokeren/internal/safety"
)

type FileChange struct {
	Path   string  `json:"path"`
	Action string  `json:"action"`
	Before *string `json:"before"`
	After  *string `json:"after"`
}

type Entry struct {
	ID          int            `json:"id"`
	Timestamp   float64        `json:"timestamp"`
	ToolName    string         `json:"tool_name"`
	ToolArgs    map[string]any `json:"tool_args"`
	ToolResult  map[string]any `json:"tool_result"`
	ToolOK      bool           `json:"tool_ok"`
	FileChanges []FileChange   `json:"file_changes"`
}

type Manager struct {
	root           string
	directory      string
	maxCheckpoints int
	auto           bool
	nextID         int
}

func New(root, sessionID string, maxCheckpoints int, auto bool) (*Manager, error) {
	if strings.TrimSpace(sessionID) == "" {
		sessionID = "default"
	}
	if maxCheckpoints <= 0 {
		maxCheckpoints = 50
	}
	resolved := resolveRoot(root)
	directory, err := checkpointDirectory(resolved, sessionID)
	if err != nil {
		return nil, err
	}
	manager := &Manager{root: resolved, directory: directory, maxCheckpoints: maxCheckpoints, auto: auto, nextID: 1}
	if ids, err := manager.ids(); err == nil && len(ids) > 0 {
		manager.nextID = ids[len(ids)-1] + 1
	}
	return manager, nil
}

func (m *Manager) Enabled() bool {
	return m != nil && m.auto
}

func (m *Manager) Directory() string {
	if m == nil {
		return ""
	}
	return m.directory
}

func (m *Manager) Snapshot(toolName string, args map[string]any) map[string]*string {
	if m == nil || (toolName != "write_file" && toolName != "patch_file") {
		return nil
	}
	path, _ := args["path"].(string)
	if path == "" {
		return nil
	}
	content, exists := m.readProjectFile(path)
	if !exists {
		return map[string]*string{path: nil}
	}
	return map[string]*string{path: &content}
}

func (m *Manager) Save(toolName string, args map[string]any, result map[string]any, ok bool, before map[string]*string) (Entry, error) {
	if m == nil {
		return Entry{}, nil
	}
	changes := m.detectChanges(toolName, args, before)
	entry := Entry{ID: m.nextID, Timestamp: float64(time.Now().UnixNano()) / 1e9, ToolName: toolName, ToolArgs: args, ToolResult: result, ToolOK: ok, FileChanges: changes}
	data, err := json.MarshalIndent(entry, "", "  ")
	if err != nil {
		return Entry{}, fmt.Errorf("serialisasi checkpoint: %w", err)
	}
	if err := writeFileAtomic(m.entryPath(entry.ID), data); err != nil {
		return Entry{}, fmt.Errorf("simpan checkpoint: %w", err)
	}
	m.nextID++
	if err := m.rotate(); err != nil {
		return Entry{}, err
	}
	meta, _ := json.MarshalIndent(map[string]int{"next_id": m.nextID}, "", "  ")
	if err := writeFileAtomic(filepath.Join(m.directory, "meta.json"), meta); err != nil {
		return Entry{}, fmt.Errorf("simpan metadata checkpoint: %w", err)
	}
	return entry, nil
}

func (m *Manager) Rewind(steps int) ([]Entry, error) {
	if m == nil {
		return nil, errors.New("time-travel tidak diaktifkan")
	}
	if steps < 1 {
		steps = 1
	}
	ids, err := m.ids()
	if err != nil {
		return nil, err
	}
	if len(ids) == 0 {
		return nil, nil
	}
	if steps > len(ids) {
		steps = len(ids)
	}
	targets := ids[len(ids)-steps:]
	undone := make([]Entry, 0, len(targets))
	for index := len(targets) - 1; index >= 0; index-- {
		entry, err := m.load(targets[index])
		if err != nil {
			return undone, err
		}
		if err := m.revert(entry.FileChanges); err != nil {
			return undone, err
		}
		if err := os.Remove(m.entryPath(entry.ID)); err != nil && !os.IsNotExist(err) {
			return undone, err
		}
		undone = append(undone, entry)
	}
	if len(undone) > 0 {
		m.nextID = undone[len(undone)-1].ID
		meta, _ := json.MarshalIndent(map[string]int{"next_id": m.nextID}, "", "  ")
		if err := writeFileAtomic(filepath.Join(m.directory, "meta.json"), meta); err != nil {
			return undone, err
		}
	}
	return undone, nil
}

func (m *Manager) List() ([]Entry, error) {
	if m == nil {
		return nil, nil
	}
	ids, err := m.ids()
	if err != nil {
		return nil, err
	}
	entries := make([]Entry, 0, len(ids))
	for _, id := range ids {
		entry, err := m.load(id)
		if err != nil {
			return nil, err
		}
		entries = append(entries, entry)
	}
	return entries, nil
}

func (m *Manager) Count() int {
	entries, err := m.List()
	if err != nil {
		return 0
	}
	return len(entries)
}

func (m *Manager) detectChanges(toolName string, args map[string]any, before map[string]*string) []FileChange {
	if toolName != "write_file" && toolName != "patch_file" {
		return nil
	}
	path, _ := args["path"].(string)
	if path == "" {
		return nil
	}
	prior, tracked := before[path]
	if !tracked {
		return nil
	}
	afterText, exists := m.readProjectFile(path)
	if prior == nil && exists {
		return []FileChange{{Path: path, Action: "create", After: &afterText}}
	}
	if prior != nil && exists && *prior != afterText {
		return []FileChange{{Path: path, Action: "modify", Before: prior, After: &afterText}}
	}
	if prior != nil && !exists {
		return []FileChange{{Path: path, Action: "delete", Before: prior}}
	}
	return nil
}

func (m *Manager) revert(changes []FileChange) error {
	for index := len(changes) - 1; index >= 0; index-- {
		change := changes[index]
		path, err := projectPath(m.root, change.Path)
		if err != nil {
			return err
		}
		switch change.Action {
		case "create":
			if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
				return err
			}
		case "modify", "delete":
			if change.Before != nil {
				if err := writeFileAtomic(path, []byte(*change.Before)); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

func (m *Manager) readProjectFile(path string) (string, bool) {
	target, err := projectPath(m.root, path)
	if err != nil {
		return "", false
	}
	data, err := os.ReadFile(target)
	if err != nil {
		return "", false
	}
	return string(data), true
}

func (m *Manager) load(id int) (Entry, error) {
	data, err := os.ReadFile(m.entryPath(id))
	if err != nil {
		return Entry{}, err
	}
	var entry Entry
	if err := json.Unmarshal(data, &entry); err != nil {
		return Entry{}, fmt.Errorf("baca checkpoint %d: %w", id, err)
	}
	return entry, nil
}

func (m *Manager) ids() ([]int, error) {
	entries, err := os.ReadDir(m.directory)
	if err != nil {
		return nil, err
	}
	ids := make([]int, 0)
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" || entry.Name() == "meta.json" {
			continue
		}
		var id int
		if _, err := fmt.Sscanf(strings.TrimSuffix(entry.Name(), ".json"), "%d", &id); err == nil && id > 0 {
			ids = append(ids, id)
		}
	}
	sort.Ints(ids)
	return ids, nil
}

func (m *Manager) rotate() error {
	ids, err := m.ids()
	if err != nil {
		return err
	}
	for len(ids) > m.maxCheckpoints {
		if err := os.Remove(m.entryPath(ids[0])); err != nil {
			return err
		}
		ids = ids[1:]
	}
	return nil
}

func (m *Manager) entryPath(id int) string {
	return filepath.Join(m.directory, fmt.Sprintf("%04d.json", id))
}

func checkpointDirectory(root, sessionID string) (string, error) {
	primary := filepath.Join(root, ".ak-checkpoints", "session-"+sessionID)
	if err := testDirectory(primary); err == nil {
		return primary, nil
	}
	fallback := filepath.Join(configBase(), "projects", projectSlug(root), ".ak-checkpoints", "session-"+sessionID)
	if err := testDirectory(fallback); err != nil {
		return "", err
	}
	return fallback, nil
}

func testDirectory(directory string) error {
	if err := os.MkdirAll(directory, 0o700); err != nil {
		return err
	}
	file, err := os.CreateTemp(directory, ".write-test-")
	if err != nil {
		return err
	}
	name := file.Name()
	if closeErr := file.Close(); closeErr != nil {
		return closeErr
	}
	return os.Remove(name)
}

func writeFileAtomic(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	file, err := os.CreateTemp(filepath.Dir(path), ".checkpoint-")
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

func projectPath(root, requested string) (string, error) {
	return safety.ProjectPath(root, requested)
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
