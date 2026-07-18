package memory

import (
	"crypto/md5"
	"database/sql"
	"encoding/hex"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode"

	_ "modernc.org/sqlite"
)

const (
	maxContextRunes = 3000
	maxMemoryLines  = 200
	maxStoredRunes  = 12000
)

var (
	sensitiveAssignment = regexp.MustCompile(`(?i)(["']?(?:api[_-]?key|password|secret|token|authorization)["']?\s*[:=]\s*["']?)([^\s,"'}\]]+)`)
	bearerToken         = regexp.MustCompile(`(?i)\bbearer\s+[a-z0-9._~+/=-]+`)
	bareToken           = regexp.MustCompile(`(?i)\b(?:sk|ak|cf|aiza)[_-][a-z0-9._-]{8,}\b`)
)

type Store struct {
	root       string
	projectDir string
	path       string
	database   string
	legacyPath string
}

func New(root string) Store {
	resolved := resolveRoot(root)
	projectDir := filepath.Join(configBase(), "projects", projectSlug(resolved))
	return Store{
		root:       resolved,
		projectDir: projectDir,
		path:       filepath.Join(projectDir, "memory.md"),
		database:   filepath.Join(projectDir, "memory.db"),
		legacyPath: filepath.Join(resolved, ".autokeren", "memory.md"),
	}
}

func (s Store) Path() string {
	return s.path
}

func (s Store) DatabasePath() string {
	return s.database
}

func (s Store) ProjectDir() string {
	return s.projectDir
}

func (s Store) LegacyPath() string {
	return s.legacyPath
}

func (s Store) Ensure() error {
	if err := os.MkdirAll(s.projectDir, 0o700); err != nil {
		return fmt.Errorf("buat direktori memory: %w", err)
	}
	if err := s.migrateLegacy(); err != nil {
		return err
	}
	if err := s.initializeDB(); err != nil {
		return err
	}
	if info, err := os.Stat(s.path); err != nil || info.Size() == 0 {
		if err := s.writeMemory(s.defaultMemory()); err != nil {
			return err
		}
	}
	return nil
}

func (s Store) Append(section, note string) error {
	section = cleanLine(section)
	note = cleanLine(redactSensitive(note))
	if section == "" || note == "" {
		return os.ErrInvalid
	}
	if err := s.Ensure(); err != nil {
		return err
	}
	existing, err := os.ReadFile(filepath.Clean(s.path))
	if err != nil {
		return fmt.Errorf("baca memory: %w", err)
	}
	content := string(existing)
	header := "## " + section
	if index := strings.Index(content, header+"\n"); index >= 0 {
		insertAt := index + len(header) + 1
		content = content[:insertAt] + "- " + note + "\n" + content[insertAt:]
	} else {
		if content != "" && !strings.HasSuffix(content, "\n") {
			content += "\n"
		}
		content += "\n" + header + "\n_Update: " + time.Now().UTC().Format("2006-01-02") + "_\n- " + note + "\n"
	}
	if err := s.writeMemory(content); err != nil {
		return err
	}
	return s.insertLesson(section, note)
}

func (s Store) LogMessage(sessionID, role, content string) error {
	if strings.TrimSpace(role) == "" || strings.TrimSpace(content) == "" {
		return nil
	}
	if err := s.Ensure(); err != nil {
		return err
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", cleanLine(sessionID), cleanLine(role), redactSensitive(content))
	if err != nil {
		return fmt.Errorf("simpan pesan memory: %w", err)
	}
	return nil
}

func (s Store) Load() string {
	if err := s.Ensure(); err != nil {
		return ""
	}
	data, err := os.ReadFile(filepath.Clean(s.path))
	if err != nil {
		return ""
	}
	lines := strings.Split(string(data), "\n")
	if len(lines) > maxMemoryLines {
		lines = lines[:maxMemoryLines]
	}
	return strings.Join(lines, "\n")
}

func (s Store) Search(query string, limit int) []string {
	if limit <= 0 || strings.TrimSpace(query) == "" {
		return nil
	}
	if err := s.Ensure(); err != nil {
		return nil
	}
	documents := s.documents()
	if len(documents) == 0 {
		return nil
	}
	queryTokens := tokens(query)
	if len(queryTokens) == 0 {
		return nil
	}
	docTokens := make([][]string, len(documents))
	documentFrequency := map[string]int{}
	for index, document := range documents {
		docTokens[index] = tokens(document)
		seen := map[string]struct{}{}
		for _, token := range docTokens[index] {
			seen[token] = struct{}{}
		}
		for token := range seen {
			documentFrequency[token]++
		}
	}
	queryVector := weighted(queryTokens, documentFrequency, len(documents))
	queryNorm := norm(queryVector)
	if queryNorm == 0 {
		return nil
	}
	type scored struct {
		value float64
		text  string
	}
	results := make([]scored, 0, len(documents))
	for index, document := range documents {
		vector := weighted(docTokens[index], documentFrequency, len(documents))
		score := cosine(queryVector, queryNorm, vector)
		if score <= 0.05 {
			continue
		}
		results = append(results, scored{value: score, text: document})
	}
	sort.SliceStable(results, func(left, right int) bool { return results[left].value > results[right].value })
	if len(results) > limit {
		results = results[:limit]
	}
	output := make([]string, 0, len(results))
	for _, result := range results {
		output = append(output, result.text)
	}
	return output
}

func (s Store) Context(query string, limit int) string {
	notes := s.Search(query, limit)
	if len(notes) == 0 {
		return ""
	}
	return limitRunes("Memori proyek relevan:\n"+bulletList(notes), maxContextRunes)
}

func (s Store) documents() []string {
	seen := map[string]struct{}{}
	documents := make([]string, 0)
	data, err := os.ReadFile(filepath.Clean(s.path))
	if err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			line = strings.TrimSpace(line)
			if !strings.HasPrefix(line, "- ") {
				continue
			}
			note := strings.TrimSpace(strings.TrimPrefix(line, "- "))
			if note == "" {
				continue
			}
			if _, exists := seen[note]; exists {
				continue
			}
			seen[note] = struct{}{}
			documents = append(documents, note)
		}
	}
	db, err := s.open()
	if err != nil {
		return documents
	}
	defer db.Close()
	rows, err := db.Query("SELECT pattern, task_title, lesson FROM lessons")
	if err != nil {
		return documents
	}
	defer rows.Close()
	for rows.Next() {
		var pattern, title, lesson string
		if err := rows.Scan(&pattern, &title, &lesson); err != nil {
			continue
		}
		note := "[" + pattern + "] " + title + ": " + lesson
		if _, exists := seen[note]; exists {
			continue
		}
		seen[note] = struct{}{}
		documents = append(documents, note)
	}
	return documents
}

func (s Store) insertLesson(section, note string) error {
	title := "manual_note"
	if strings.Contains(section, "autoplan") {
		title = section
	}
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec("INSERT INTO lessons (pattern, task_title, lesson, success) VALUES (?, ?, ?, ?)", section, title, note, 1)
	if err != nil {
		return fmt.Errorf("simpan pelajaran memory: %w", err)
	}
	return nil
}

func (s Store) initializeDB() error {
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS messages (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		session_id TEXT,
		role TEXT,
		content TEXT,
		timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
	)`); err != nil {
		return fmt.Errorf("inisialisasi pesan memory: %w", err)
	}
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS lessons (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		pattern TEXT,
		task_title TEXT,
		lesson TEXT,
		success INTEGER,
		timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
	)`); err != nil {
		return fmt.Errorf("inisialisasi lessons memory: %w", err)
	}
	return nil
}

func (s Store) open() (*sql.DB, error) {
	db, err := sql.Open("sqlite", s.database)
	if err != nil {
		return nil, fmt.Errorf("buka database memory: %w", err)
	}
	if _, err := db.Exec("PRAGMA busy_timeout = 5000"); err != nil {
		db.Close()
		return nil, fmt.Errorf("atur database memory: %w", err)
	}
	return db, nil
}

func (s Store) migrateLegacy() error {
	if _, err := os.Stat(s.path); err == nil {
		return nil
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("periksa memory kompatibel: %w", err)
	}
	legacy, err := os.ReadFile(filepath.Clean(s.legacyPath))
	if errorsIsNotExist(err) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("baca memory Go lama: %w", err)
	}
	backup := filepath.Join(s.projectDir, "memory.go-legacy-backup.md")
	if err := writeFileAtomic(backup, legacy); err != nil {
		return fmt.Errorf("backup memory Go lama: %w", err)
	}
	if err := s.writeMemory(string(legacy)); err != nil {
		return fmt.Errorf("migrasi memory Go lama: %w", err)
	}
	return nil
}

func (s Store) writeMemory(content string) error {
	if err := writeFileAtomic(s.path, []byte(content)); err != nil {
		return fmt.Errorf("simpan memory: %w", err)
	}
	return nil
}

func (s Store) defaultMemory() string {
	name := filepath.Base(s.root)
	if name == "." || name == string(filepath.Separator) || name == "" {
		name = "default"
	}
	stacks := make([]string, 0, 5)
	if fileExists(filepath.Join(s.root, "package.json")) {
		stacks = append(stacks, "Node.js")
	}
	if fileExists(filepath.Join(s.root, "requirements.txt")) || fileExists(filepath.Join(s.root, "pyproject.toml")) || fileExists(filepath.Join(s.root, "setup.py")) {
		stacks = append(stacks, "Python")
	}
	if fileExists(filepath.Join(s.root, "go.mod")) {
		stacks = append(stacks, "Go")
	}
	if fileExists(filepath.Join(s.root, "Cargo.toml")) {
		stacks = append(stacks, "Rust")
	}
	if fileExists(filepath.Join(s.root, "wrangler.toml")) || fileExists(filepath.Join(s.root, "wrangler.json")) {
		stacks = append(stacks, "Cloudflare Workers")
	}
	techStack := strings.Join(stacks, ", ")
	if techStack == "" {
		techStack = "Unknown"
	}
	return "# Project Memory: " + name + "\n\n" +
		"## Metadata Proyek\n" +
		"- **Nama Project**: " + name + "\n" +
		"- **Direktori**: " + s.root + "\n" +
		"- **Teknologi**: " + techStack + "\n" +
		"- **Link Frontend (FE)**: (Silakan diisi, contoh: http://localhost:3000)\n" +
		"- **Link Backend (BE)**: (Silakan diisi, contoh: http://localhost:8787)\n\n" +
		"## Panduan / Runbook\n" +
		"- **Install Dependencies**: (contoh: npm install atau pip install)\n" +
		"- **Jalankan Aplikasi**: (contoh: npm run dev)\n" +
		"- **Jalankan Pengujian**: (contoh: pytest atau npm test)\n\n" +
		"## Catatan Kunci & Context\n" +
		"- Proyek ini dikelola menggunakan autokeren CLI.\n"
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
	name := sanitizeFilename(filepath.Base(root))
	if name == "" {
		name = "default"
	}
	sum := md5.Sum([]byte(root))
	return name + "-" + hex.EncodeToString(sum[:])[:8]
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

func sanitizeFilename(value string) string {
	return strings.Trim(strings.Map(func(r rune) rune {
		if unicode.IsLetter(r) || unicode.IsNumber(r) || r == '_' || r == '-' || r == '.' {
			return r
		}
		return '_'
	}, value), "._")
}

func redactSensitive(value string) string {
	value = sensitiveAssignment.ReplaceAllString(value, "$1[REDACTED]")
	value = bearerToken.ReplaceAllStringFunc(value, func(match string) string {
		return "Bearer [REDACTED]"
	})
	value = bareToken.ReplaceAllString(value, "[REDACTED]")
	return limitRunes(value, maxStoredRunes)
}

func writeFileAtomic(path string, data []byte) error {
	directory := filepath.Dir(path)
	if err := os.MkdirAll(directory, 0o700); err != nil {
		return err
	}
	file, err := os.CreateTemp(directory, ".memory-*")
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

func errorsIsNotExist(err error) bool {
	return err != nil && os.IsNotExist(err)
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func tokens(value string) []string {
	return strings.FieldsFunc(strings.ToLower(value), func(r rune) bool { return !unicode.IsLetter(r) && !unicode.IsNumber(r) })
}

func weighted(input []string, documentFrequency map[string]int, totalDocuments int) map[string]float64 {
	counts := map[string]int{}
	for _, token := range input {
		counts[token]++
	}
	vector := make(map[string]float64, len(counts))
	for token, count := range counts {
		idf := math.Log(float64(totalDocuments+1)/float64(documentFrequency[token]+1)) + 1
		vector[token] = float64(count) * idf
	}
	return vector
}

func cosine(left map[string]float64, leftNorm float64, right map[string]float64) float64 {
	rightNorm := norm(right)
	if leftNorm == 0 || rightNorm == 0 {
		return 0
	}
	dot := 0.0
	for token, value := range left {
		dot += value * right[token]
	}
	return dot / (leftNorm * rightNorm)
}

func norm(vector map[string]float64) float64 {
	total := 0.0
	for _, value := range vector {
		total += value * value
	}
	return math.Sqrt(total)
}

func bulletList(notes []string) string {
	var builder strings.Builder
	for _, note := range notes {
		builder.WriteString("- ")
		builder.WriteString(note)
		builder.WriteByte('\n')
	}
	return strings.TrimSpace(builder.String())
}

func cleanLine(value string) string {
	return strings.Join(strings.Fields(value), " ")
}

func limitRunes(value string, max int) string {
	runes := []rune(value)
	if len(runes) <= max {
		return value
	}
	return string(runes[:max]) + "\n[Memori dipotong agar context tetap aman]"
}
