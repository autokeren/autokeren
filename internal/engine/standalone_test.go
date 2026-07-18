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

	"github.com/autokeren/autokeren/internal/checkpoint"
	"github.com/autokeren/autokeren/internal/config"
	"github.com/autokeren/autokeren/internal/memory"
	"github.com/autokeren/autokeren/internal/model"
	"github.com/autokeren/autokeren/internal/session"
	"github.com/autokeren/autokeren/internal/tool"
	"github.com/autokeren/autokeren/internal/workflow"
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

func TestSafeDeployBlocksPublishWithoutApprovedProof(t *testing.T) {
	requests := 0
	safeToolNames := map[string]bool{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests++
		if requests == 1 {
			var request model.Request
			if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
				t.Error(err)
				return
			}
			for _, definition := range request.Tools {
				safeToolNames[definition.Function.Name] = true
			}
		}
		w.Header().Set("Content-Type", "text/event-stream")
		if requests == 1 {
			_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"id\":\"publish-1\",\"type\":\"function\",\"function\":{\"name\":\"publish_app\",\"arguments\":\"{\\\"name\\\":\\\"shoe-store\\\"}\"}}]}}]}\n\ndata: [DONE]\n\n"))
			return
		}
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"publish diblokir sampai proof disetujui\"},\"finish_reason\":\"stop\"}]}\n\ndata: [DONE]\n\n"))
	}))
	defer server.Close()
	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Retry.MaxRetries = 0
	prompt, handled, err := workflow.Expand("/safe-deploy landing page toko sepatu")
	if err != nil || !handled {
		t.Fatalf("safe deploy expansion failed: prompt=%q handled=%t err=%v", prompt, handled, err)
	}
	var publishResult string
	content, err := RunStandaloneEvents(t.Context(), cfg, t.TempDir(), prompt, Events{OnToolEnd: func(name string, result tool.Result) {
		if name == "publish_app" {
			publishResult = result.Error
		}
	}}, "")
	if err != nil || content != "publish diblokir sampai proof disetujui" {
		t.Fatalf("unexpected safe deploy result: content=%q err=%v", content, err)
	}
	if !strings.Contains(publishResult, "proof_id") {
		t.Fatalf("publish was not proof-gated: %q", publishResult)
	}
	for _, forbidden := range []string{"cf_deploy", "deploy_project"} {
		if safeToolNames[forbidden] {
			t.Fatalf("safe deploy exposed legacy bypass tool %q", forbidden)
		}
	}
}

func TestRunStandaloneRecoversMalformedToolCallBeforeStrictProviderRejectsHistory(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	requests := 0
	recoverySeen := false
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, request *http.Request) {
		requests++
		w.Header().Set("Content-Type", "text/event-stream")
		if requests == 1 {
			_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"id\":\"broken-call\",\"type\":\"function\",\"function\":{\"name\":\"run_shell\",\"arguments\":\"{\\\"command\\\":\\\"pwd\\\"\"}}]}}]}\n\ndata: [DONE]\n\n"))
			return
		}
		var payload model.Request
		if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		for _, message := range payload.Messages {
			if message.Role == "assistant" {
				for _, call := range message.ToolCalls {
					if !json.Valid([]byte(call.Function.Arguments)) {
						http.Error(w, "Assistant tool call function.arguments must be valid JSON.", http.StatusBadRequest)
						return
					}
				}
			}
			if message.Role == "system" && strings.Contains(message.Content, "format argumennya rusak") {
				recoverySeen = true
			}
		}
		if requests == 2 {
			_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"id\":\"list-files\",\"type\":\"function\",\"function\":{\"name\":\"list_files\",\"arguments\":\"{\\\"path\\\":\\\".\\\"}\"}}]}}]}\n\ndata: [DONE]\n\n"))
			return
		}
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"pulih dan lanjut\"},\"finish_reason\":\"stop\"}]}\n\ndata: [DONE]\n\n"))
	}))
	defer server.Close()
	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Retry.MaxRetries = 0
	content, err := RunStandalone(t.Context(), cfg, root, "cek project", nil, "")
	if err != nil || content != "pulih dan lanjut" || requests != 3 || !recoverySeen {
		t.Fatalf("malformed call tidak pulih: content=%q err=%v requests=%d recovery=%t", content, err, requests, recoverySeen)
	}
}

func TestRunStandaloneWritesCheckpointAndRewindsFile(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	calls := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		calls++
		w.Header().Set("Content-Type", "text/event-stream")
		if calls == 1 {
			_, _ = w.Write([]byte("data: {\"model\":\"test\",\"choices\":[{\"delta\":{\"tool_calls\":[{\"index\":0,\"id\":\"write-1\",\"type\":\"function\",\"function\":{\"name\":\"write_file\",\"arguments\":\"{\\\"path\\\":\\\"checkpointed.txt\\\",\\\"content\\\":\\\"selamat\\\"}\"}}]}}]}\n\n"))
			_, _ = w.Write([]byte("data: [DONE]\n\n"))
			return
		}
		_, _ = w.Write([]byte("data: {\"model\":\"test\",\"choices\":[{\"delta\":{\"content\":\"berhasil\"},\"finish_reason\":\"stop\"}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()
	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Retry.MaxRetries = 0
	content, err := RunStandalone(t.Context(), cfg, root, "buat file", nil, "")
	if err != nil || content != "berhasil" || calls != 2 {
		t.Fatalf("standalone write gagal: content=%q err=%v calls=%d", content, err, calls)
	}
	if data, err := os.ReadFile(filepath.Join(root, "checkpointed.txt")); err != nil || string(data) != "selamat" {
		t.Fatalf("file belum ditulis: data=%q err=%v", data, err)
	}
	manager, err := checkpoint.New(root, "default", cfg.Autokeren.TimeTravel.MaxCheckpoints, true)
	if err != nil {
		t.Fatal(err)
	}
	if manager.Count() != 1 {
		t.Fatalf("checkpoint tidak tersimpan: count=%d", manager.Count())
	}
	if _, err := manager.Rewind(1); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(root, "checkpointed.txt")); !os.IsNotExist(err) {
		t.Fatalf("rewind standalone tidak memulihkan file: %v", err)
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

func TestRunStandaloneUsesFDDMLifecycleWithoutChangingResponse(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	var mu sync.Mutex
	calls := make([]string, 0)
	var modelMessages []model.Message
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		calls = append(calls, r.URL.Path)
		mu.Unlock()
		switch r.URL.Path {
		case "/api/sniff_text":
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`[{"type":"decision","score":0.8,"artifact":"gunakan retry aman"}]`))
		case "/api/emit_text":
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{"scent_id":"saved"}`))
		default:
			var request struct {
				Messages []model.Message `json:"messages"`
			}
			if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
				t.Error(err)
				return
			}
			modelMessages = request.Messages
			w.Header().Set("Content-Type", "text/event-stream")
			_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"hasil tugas sudah selesai dengan verifikasi aman\"},\"finish_reason\":\"stop\"}]}\n\n"))
			_, _ = w.Write([]byte("data: [DONE]\n\n"))
		}
	}))
	defer server.Close()
	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Retry.MaxRetries = 0
	cfg.Autokeren.FDDM = config.FDDM{Enabled: true, URL: server.URL, APIKey: "fddm-key"}
	content, err := RunStandalone(t.Context(), cfg, root, "cek retry", nil, "")
	if err != nil || content != "hasil tugas sudah selesai dengan verifikasi aman" {
		t.Fatalf("content=%q err=%v", content, err)
	}
	joinedMessages := ""
	for _, message := range modelMessages {
		joinedMessages += message.Content + "\n"
	}
	if !strings.Contains(joinedMessages, "FDDM AUTO-SNIFF") || !strings.Contains(joinedMessages, "gunakan retry aman") {
		t.Fatalf("context FDDM tidak masuk ke request model: %s", joinedMessages)
	}
	mu.Lock()
	defer mu.Unlock()
	if len(calls) != 3 || calls[0] != "/api/sniff_text" || calls[2] != "/api/emit_text" {
		t.Fatalf("urutan lifecycle FDDM = %#v", calls)
	}
}

func TestRunStandaloneContinuesWhenFDDMUnavailable(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/api/") {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"model tetap responsif ketika FDDM gagal\"},\"finish_reason\":\"stop\"}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()
	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	cfg.Auth.APIKey = "test-key"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Retry.MaxRetries = 0
	cfg.Autokeren.FDDM = config.FDDM{Enabled: true, URL: server.URL}
	var savedID string
	content, err := RunStandaloneEvents(t.Context(), cfg, root, "cek FDDM", Events{OnSessionSaved: func(id, _ string) { savedID = id }}, "")
	if err != nil || content != "model tetap responsif ketika FDDM gagal" || savedID == "" {
		t.Fatalf("FDDM outage mengganggu task: content=%q err=%v session=%q", content, err, savedID)
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
