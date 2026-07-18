package engine

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/autokeren/autokeren/internal/config"
	"github.com/autokeren/autokeren/internal/memory"
	"github.com/autokeren/autokeren/internal/model"
	"github.com/autokeren/autokeren/internal/session"
)

func TestRunStandaloneFallsBackToSecondaryModel(t *testing.T) {
	var mu sync.Mutex
	models := []string{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var request struct {
			Model string `json:"model"`
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Error(err)
			return
		}
		mu.Lock()
		models = append(models, request.Model)
		mu.Unlock()
		if request.Model == "primary" {
			w.WriteHeader(http.StatusServiceUnavailable)
			_, _ = w.Write([]byte("primary unavailable"))
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"model\":\"secondary\",\"choices\":[{\"delta\":{\"content\":\"fallback siap\"},\"finish_reason\":\"stop\"}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()

	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Cloudflare.PrimaryModel = "primary"
	cfg.Cloudflare.SecondaryModel = "secondary"
	cfg.Retry.MaxRetries = 0
	cfg.Retry.CircuitFailureThreshold = 1

	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	content, err := RunStandalone(t.Context(), cfg, root, "halo", nil, "")
	if err != nil {
		t.Fatal(err)
	}
	if content != "fallback siap" {
		t.Fatalf("content = %q", content)
	}
	mu.Lock()
	defer mu.Unlock()
	if len(models) != 2 || models[0] != "primary" || models[1] != "secondary" {
		t.Fatalf("models = %#v", models)
	}
}

func TestRunStandaloneInjectsGuidanceAndRelevantMemory(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	if err := os.WriteFile(filepath.Join(root, "AGENTS.md"), []byte("Gunakan command go test sebelum commit."), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := memory.New(root).Append("build", "Untuk router, jalankan go test ./... sebelum commit."); err != nil {
		t.Fatal(err)
	}
	var messages []model.Message
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var request struct {
			Messages []model.Message `json:"messages"`
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Error(err)
			return
		}
		messages = request.Messages
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"siap\"},\"finish_reason\":\"stop\"}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()

	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Retry.MaxRetries = 0
	content, err := RunStandalone(t.Context(), cfg, root, "cek router", nil, "")
	if err != nil || content != "siap" {
		t.Fatalf("content=%q err=%v", content, err)
	}
	joined := ""
	for _, message := range messages {
		if message.Role == "system" {
			joined += message.Content + "\n"
		}
	}
	for _, expected := range []string{"Gunakan command go test sebelum commit.", "Untuk router, jalankan go test"} {
		if !strings.Contains(joined, expected) {
			t.Fatalf("missing %q in system messages: %s", expected, joined)
		}
	}
}

func TestRunStandaloneRecordsRedactedMemoryTranscript(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"deploy siap\"},\"finish_reason\":\"stop\"}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()
	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Retry.MaxRetries = 0
	secret := "sk-live-abcdefghijklmno"
	if _, err := RunStandalone(t.Context(), cfg, root, "cek api_key="+secret, nil, ""); err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", memory.New(root).DatabasePath())
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	rows, err := db.Query("SELECT role, content FROM messages ORDER BY id")
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	entries := make([]string, 0)
	for rows.Next() {
		var role, content string
		if err := rows.Scan(&role, &content); err != nil {
			t.Fatal(err)
		}
		entries = append(entries, role+":"+content)
	}
	joined := strings.Join(entries, "\n")
	if !strings.Contains(joined, "user:") || !strings.Contains(joined, "assistant:deploy siap") {
		t.Fatalf("transkrip memory tidak lengkap: %s", joined)
	}
	if strings.Contains(joined, secret) {
		t.Fatalf("secret bocor ke transkrip memory: %s", joined)
	}
}

func TestRunStandalonePersistsSessionWhenProviderFails(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
		_, _ = w.Write([]byte("sementara tidak tersedia"))
	}))
	defer server.Close()

	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Retry.MaxRetries = 0
	var savedID string
	_, err := RunStandaloneEvents(t.Context(), cfg, root, "jangan hilangkan prompt ini", Events{
		OnSessionSaved: func(id, _ string) { savedID = id },
	}, "")
	if err == nil {
		t.Fatal("expected provider failure")
	}
	if savedID == "" {
		t.Fatal("failed run must still save a recoverable session")
	}
	sessions, err := session.NewManager(root)
	if err != nil {
		t.Fatal(err)
	}
	data, err := sessions.Load(savedID)
	if err != nil {
		t.Fatal(err)
	}
	serialized, err := json.Marshal(data.Messages)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(serialized), "jangan hilangkan prompt ini") {
		t.Fatalf("saved session omitted failed prompt: %s", serialized)
	}
}

func TestCompactTailTurnsPreservesPythonMinimum(t *testing.T) {
	if got := compactTailTurns(6); got != 12 {
		t.Fatalf("compact tail = %d, want 12", got)
	}
	if got := compactTailTurns(18); got != 18 {
		t.Fatalf("configured compact tail was reduced: %d", got)
	}
}

func TestDefaultPermissionMakesGhostReadOnlyUnlessCapabilityGranted(t *testing.T) {
	t.Setenv("AUTOKEREN_GHOST_CHILD", "1")
	t.Setenv("AUTOKEREN_GHOST_ALLOWED_TOOLS", "patch_file,run_shell")
	if !defaultPermission("patch_file", "", nil) || !defaultPermission("run_shell", "", nil) || defaultPermission("write_file", "", nil) {
		t.Fatal("ghost capability policy is not least privilege")
	}
	t.Setenv("AUTOKEREN_GHOST_CHILD", "")
	if !defaultPermission("write_file", "", nil) || defaultPermission("run_shell", "", nil) {
		t.Fatal("normal standalone permission behavior changed unexpectedly")
	}
}
