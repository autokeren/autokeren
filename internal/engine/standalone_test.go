package engine

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"

	"github.com/autokeren/autokeren/internal/config"
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
