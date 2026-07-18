package engine

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/autokeren/autokeren/internal/config"
)

func TestDirectorWorkerMailboxEndToEnd(t *testing.T) {
	var mu sync.Mutex
	requests := make([]map[string]any, 0)
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/v1/chat/completions" {
			http.NotFound(writer, request)
			return
		}
		var payload map[string]any
		if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
			http.Error(writer, err.Error(), http.StatusBadRequest)
			return
		}
		mu.Lock()
		requests = append(requests, payload)
		mu.Unlock()
		writer.Header().Set("Content-Type", "text/event-stream")
		messages, _ := payload["messages"].([]any)
		if hasToolResult(messages, "spawn_agent") {
			_, _ = writer.Write([]byte("data: {\"model\":\"local-e2e\",\"choices\":[{\"delta\":{\"content\":\"director lanjut tanpa menunggu worker\"}}]}\n\ndata: [DONE]\n\n"))
			return
		}
		if hasUserText(messages, "DIRECTOR_E2E") {
			event := "data: {\"model\":\"local-e2e\",\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"id\":\"spawn-e2e\",\"type\":\"function\",\"function\":{\"name\":\"spawn_agent\",\"arguments\":\"{\\\"task\\\":\\\"subtask e2e\\\",\\\"role\\\":\\\"reviewer\\\",\\\"background\\\":true}\"}}]}}]}\n\n"
			_, _ = writer.Write([]byte(event + event + event + "data: [DONE]\n\n"))
			return
		}
		_, _ = writer.Write([]byte("data: {\"model\":\"local-e2e\",\"choices\":[{\"delta\":{\"content\":\"bukti worker: test lulus\"}}]}\n\ndata: [DONE]\n\n"))
	}))
	defer server.Close()

	root := t.TempDir()
	repoRoot := repositoryRoot(t)
	binaryName := "autokeren-cli"
	if runtime.GOOS == "windows" {
		binaryName += ".exe"
	}
	binary := filepath.Join(root, binaryName)
	build := exec.Command("go", "build", "-o", binary, ".")
	build.Dir = repoRoot
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build worker binary: %v\n%s", err, output)
	}
	home := filepath.Join(root, "home")
	t.Setenv("HOME", home)
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(home, ".config", "autokeren"))
	t.Setenv("AUTOKEREN_GHOST_BIN", binary)

	cfg := config.Defaults()
	cfg.Auth.Mode = "local"
	cfg.Auth.LocalEndpoint = server.URL
	cfg.Cloudflare.PrimaryModel = "local-e2e"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Cloudflare.Timeout = 10
	if err := config.Save(filepath.Join(home, ".config", "autokeren", "config.yaml"), cfg); err != nil {
		t.Fatal(err)
	}
	content, err := RunStandalone(t.Context(), cfg, root, "DIRECTOR_E2E delegasikan review", nil, "")
	if err != nil || content != "director lanjut tanpa menunggu worker" {
		t.Fatalf("content=%q err=%v\nartifacts:\n%s", content, err, ghostArtifacts(root))
	}
	mailboxPath := filepath.Join(root, ".autokeren", "agent-mailbox.json")
	deadline := time.Now().Add(10 * time.Second)
	var mailboxData []byte
	for time.Now().Before(deadline) {
		mailboxData, _ = os.ReadFile(mailboxPath)
		if strings.Contains(string(mailboxData), "bukti worker: test lulus") {
			break
		}
		time.Sleep(25 * time.Millisecond)
	}
	if !strings.Contains(string(mailboxData), "reviewer") || !strings.Contains(string(mailboxData), "bukti worker: test lulus") || !strings.Contains(string(mailboxData), "completed") {
		t.Fatalf("unexpected mailbox: %s", mailboxData)
	}
	mu.Lock()
	count := len(requests)
	mu.Unlock()
	if count < 3 {
		t.Fatalf("expected director, worker, and mailbox requests; got %d", count)
	}
}

func ghostArtifacts(root string) string {
	entries, err := os.ReadDir(root)
	if err != nil {
		return err.Error()
	}
	parts := make([]string, 0)
	for _, entry := range entries {
		if !strings.HasPrefix(entry.Name(), ".ak-ghost-") {
			continue
		}
		data, readErr := os.ReadFile(filepath.Join(root, entry.Name()))
		if readErr != nil {
			parts = append(parts, entry.Name()+": "+readErr.Error())
			continue
		}
		parts = append(parts, entry.Name()+": "+string(data))
	}
	if len(parts) == 0 {
		return "tidak ada artifact ghost"
	}
	return strings.Join(parts, "\n")
}

func repositoryRoot(t *testing.T) string {
	t.Helper()
	workingDirectory, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	root := filepath.Clean(filepath.Join(workingDirectory, "..", ".."))
	if _, err := os.Stat(filepath.Join(root, "go.mod")); err != nil {
		t.Fatalf("repository root not found: %v", err)
	}
	return root
}

func hasToolResult(messages []any, name string) bool {
	for _, raw := range messages {
		message, ok := raw.(map[string]any)
		if ok && message["role"] == "tool" && message["name"] == name {
			return true
		}
	}
	return false
}

func hasUserText(messages []any, needle string) bool {
	for _, raw := range messages {
		message, ok := raw.(map[string]any)
		if ok && message["role"] == "user" && strings.Contains(message["content"].(string), needle) {
			return true
		}
	}
	return false
}
