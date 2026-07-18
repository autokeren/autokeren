package memory

import (
	"database/sql"
	"os"
	"path/filepath"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

func testStore(t *testing.T) Store {
	t.Helper()
	t.Setenv("AUTOKEREN_CONFIG_DIR", t.TempDir())
	return New(t.TempDir())
}

func TestStoreUsesPythonCompatiblePathsAndSchema(t *testing.T) {
	store := testStore(t)
	if err := store.Ensure(); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(store.Path(), string(filepath.Separator)+"projects"+string(filepath.Separator)) {
		t.Fatalf("memory path tidak memakai project store: %s", store.Path())
	}
	if filepath.Base(store.Path()) != "memory.md" || filepath.Base(store.DatabasePath()) != "memory.db" {
		t.Fatalf("path memory tidak kompatibel: %s, %s", store.Path(), store.DatabasePath())
	}
	db, err := sql.Open("sqlite", store.DatabasePath())
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	for _, table := range []string{"messages", "lessons"} {
		var found string
		if err := db.QueryRow("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", table).Scan(&found); err != nil {
			t.Fatalf("table Python-compatible %s tidak ada: %v", table, err)
		}
	}
}

func TestStoreReadsPythonMemoryAndLessons(t *testing.T) {
	store := testStore(t)
	if err := os.MkdirAll(store.ProjectDir(), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(store.Path(), []byte("# Memory Python\n- Gunakan Cloudflare D1 untuk data produk.\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := store.initializeDB(); err != nil {
		t.Fatal(err)
	}
	db, err := store.open()
	if err != nil {
		t.Fatal(err)
	}
	_, err = db.Exec("INSERT INTO lessons (pattern, task_title, lesson, success) VALUES (?, ?, ?, ?)", "deploy", "manual_note", "Retry 429 memakai Retry-After.", 1)
	db.Close()
	if err != nil {
		t.Fatal(err)
	}
	results := store.Search("bagaimana retry 429 saat deploy", 3)
	joined := strings.Join(results, "\n")
	if !strings.Contains(joined, "Retry-After") {
		t.Fatalf("lesson Python tidak terbaca: %#v", results)
	}
	results = store.Search("data produk di Cloudflare D1", 3)
	if !strings.Contains(strings.Join(results, "\n"), "Cloudflare D1") {
		t.Fatalf("memory.md Python tidak terbaca: %#v", results)
	}
}

func TestStoreMigratesLegacyOnceWithoutChangingSource(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", t.TempDir())
	legacyPath := filepath.Join(root, ".autokeren", "memory.md")
	legacy := "- [deploy] Worker lama menggunakan wrangler deploy.\n"
	if err := os.MkdirAll(filepath.Dir(legacyPath), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(legacyPath, []byte(legacy), 0o600); err != nil {
		t.Fatal(err)
	}
	store := New(root)
	if err := store.Ensure(); err != nil {
		t.Fatal(err)
	}
	for _, path := range []string{store.Path(), filepath.Join(store.ProjectDir(), "memory.go-legacy-backup.md"), legacyPath} {
		data, err := os.ReadFile(path)
		if err != nil || string(data) != legacy {
			t.Fatalf("migrasi tidak aman untuk %s: %q, %v", path, data, err)
		}
	}
	if err := store.Ensure(); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(store.Path())
	if err != nil || string(data) != legacy {
		t.Fatalf("migrasi kedua tidak idempotent: %q, %v", data, err)
	}
}

func TestStoreWritesPythonCompatibleRowsAndRedactsSecrets(t *testing.T) {
	store := testStore(t)
	secret := "sk-live-abcdefghijklmno"
	if err := store.Append("deploy", "Gunakan api_key="+secret+" saat deploy."); err != nil {
		t.Fatal(err)
	}
	if err := store.LogMessage("session-1", "user", "token="+secret+" tolong cek deploy"); err != nil {
		t.Fatal(err)
	}
	db, err := store.open()
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	var lesson, message string
	if err := db.QueryRow("SELECT lesson FROM lessons ORDER BY id DESC LIMIT 1").Scan(&lesson); err != nil {
		t.Fatal(err)
	}
	if err := db.QueryRow("SELECT content FROM messages ORDER BY id DESC LIMIT 1").Scan(&message); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(lesson, secret) || strings.Contains(message, secret) {
		t.Fatalf("secret tersimpan di SQLite: lesson=%q message=%q", lesson, message)
	}
	data, err := os.ReadFile(store.Path())
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(data), secret) {
		t.Fatalf("secret tersimpan di markdown: %q", data)
	}
}

func TestStoreRetrievesRelevantNotes(t *testing.T) {
	store := testStore(t)
	for _, note := range []struct{ section, text string }{
		{"build", "Jalankan go test ./... sebelum commit router."},
		{"deploy", "Worker production memakai wrangler deploy."},
		{"debug", "Router retry memakai Retry-After untuk error 429."},
	} {
		if err := store.Append(note.section, note.text); err != nil {
			t.Fatal(err)
		}
	}
	results := store.Search("bagaimana retry router saat 429", 2)
	if len(results) == 0 || !strings.Contains(results[0], "Router retry") {
		t.Fatalf("unexpected results: %#v", results)
	}
	context := store.Context("retry router", 2)
	if !strings.Contains(context, "Memori proyek relevan") || !strings.Contains(context, "Retry-After") {
		t.Fatalf("unexpected context: %s", context)
	}
}

func TestStoreDoesNotTreatHeadingsAsNotes(t *testing.T) {
	store := testStore(t)
	if err := store.Append("build", "Gunakan pytest untuk test Python."); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(store.Path(), []byte("# Heading\n- [build] Gunakan pytest untuk test Python.\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	results := store.Search("pytest", 3)
	if len(results) == 0 || strings.Contains(strings.Join(results, "\n"), "Heading") {
		t.Fatalf("unexpected results: %#v", results)
	}
}

func TestStoreLoadRespectsPythonLineLimit(t *testing.T) {
	store := testStore(t)
	if err := store.Ensure(); err != nil {
		t.Fatal(err)
	}
	lines := make([]string, 220)
	for index := range lines {
		lines[index] = "- line"
	}
	if err := os.WriteFile(store.Path(), []byte(strings.Join(lines, "\n")), 0o600); err != nil {
		t.Fatal(err)
	}
	if count := len(strings.Split(store.Load(), "\n")); count != maxMemoryLines {
		t.Fatalf("load memory lines = %d, want %d", count, maxMemoryLines)
	}
}
