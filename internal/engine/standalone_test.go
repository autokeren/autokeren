package engine

import (
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

	content, err := RunStandalone(t.Context(), cfg, t.TempDir(), "halo", nil, "")
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
