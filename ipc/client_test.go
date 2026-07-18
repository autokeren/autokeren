package ipc

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/autokeren/autokeren/ghost"
	"github.com/autokeren/autokeren/internal/config"
	"github.com/autokeren/autokeren/internal/model"
	projectstore "github.com/autokeren/autokeren/internal/project"
	"github.com/autokeren/autokeren/internal/provider"
)

func TestLocalModelsFetchesAndMarksActive(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"data":[{"id":"kimi-code","name":"Kimi K2.7 Code"},{"id":"glm-5.2"}]}`))
	}))
	defer server.Close()
	c := &Client{localConfig: config.Config{Auth: config.Auth{BaseURL: server.URL}, Cloudflare: config.Cloudflare{PrimaryModel: "glm-5.2"}}}
	models := c.localModels()
	if len(models) != 2 || models[1]["active"] != true || models[1]["name"] != "glm-5.2" {
		t.Fatalf("unexpected models: %#v", models)
	}
}

func TestLocalModelsSupportsGeminiCatalogShape(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, request *http.Request) {
		if request.Header.Get("x-goog-api-key") != "gemini-key" {
			t.Fatalf("unexpected key header: %q", request.Header.Get("x-goog-api-key"))
		}
		_, _ = w.Write([]byte(`{"models":[{"name":"models/gemini-2.5-pro"}]}`))
	}))
	defer server.Close()
	c := &Client{localConfig: config.Config{Auth: config.Auth{Mode: "aistudio", GeminiAPIKey: "gemini-key"}, Cloudflare: config.Cloudflare{PrimaryModel: "gemini-2.5-pro"}}}
	original := providerModelCatalogEndpoint
	providerModelCatalogEndpoint = func(config.Config) (provider.ModelCatalogRequest, bool) {
		return provider.ModelCatalogRequest{URL: server.URL, HeaderName: "x-goog-api-key", APIKey: "gemini-key"}, true
	}
	t.Cleanup(func() { providerModelCatalogEndpoint = original })
	models := c.localModels()
	if len(models) != 1 || models[0]["id"] != "gemini-2.5-pro" || models[0]["active"] != true {
		t.Fatalf("unexpected models: %#v", models)
	}
}

func TestLocalModelsFallbackUsesActiveProvider(t *testing.T) {
	c := &Client{localConfig: config.Config{Auth: config.Auth{Mode: "openai"}, Cloudflare: config.Cloudflare{PrimaryModel: "kimi-code"}}}
	models := c.localModels()
	if len(models) == 0 || models[0]["id"] != "gpt-5.6" {
		t.Fatalf("unexpected OpenAI fallback models: %#v", models)
	}
	for _, item := range models {
		if item["id"] == "kimi-code" {
			t.Fatalf("foreign model leaked into OpenAI selector: %#v", models)
		}
	}
}

func TestGoPlanModeRequiresApprovalInLocalSession(t *testing.T) {
	c := NewClient(nil)
	if err := c.Start(t.TempDir(), filepath.Join(t.TempDir(), "config.yaml"), map[string]interface{}{"engine": "go", "plan": true}); err != nil {
		t.Fatal(err)
	}
	defer c.Close()
	var plan map[string]any
	if err := c.callLocal("agent.run", map[string]interface{}{"user_input": "/plan"}, &plan); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(plan["content"].(string), "aktif") {
		t.Fatalf("plan mode did not start active: %#v", plan)
	}
	var approved map[string]any
	if err := c.callLocal("agent.run", map[string]interface{}{"user_input": "/approve"}, &approved); err != nil {
		t.Fatal(err)
	}
	if c.localConfig.Autokeren.PlanMode || !strings.Contains(approved["content"].(string), "disetujui") {
		t.Fatalf("approval did not unlock local plan mode: %#v", approved)
	}
}

func TestGoRuntimeLocalProviderPersistsAndResumesSession(t *testing.T) {
	var requests []map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/v1/chat/completions" {
			http.NotFound(w, request)
			return
		}
		var payload map[string]any
		if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		requests = append(requests, payload)
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"model\":\"local-test\",\"choices\":[{\"delta\":{\"content\":\"siap\"}}]}\n\ndata: [DONE]\n\n"))
	}))
	defer server.Close()

	root := t.TempDir()
	configPath := filepath.Join(root, "config.yaml")
	cfg := config.Defaults()
	cfg.Auth.Mode = "local"
	cfg.Auth.LocalEndpoint = server.URL
	cfg.Cloudflare.PrimaryModel = "local-test"
	cfg.Cloudflare.SecondaryModel = ""
	if err := config.Save(configPath, cfg); err != nil {
		t.Fatal(err)
	}

	client := NewClient(nil)
	if err := client.Start(root, configPath, map[string]interface{}{"engine": "go"}); err != nil {
		t.Fatal(err)
	}
	var first map[string]any
	if err := client.Call("agent.run", map[string]interface{}{"user_input": "halo"}, &first); err != nil {
		t.Fatal(err)
	}
	if first["content"] != "siap" || first["session_id"] == "" {
		t.Fatalf("unexpected first response: %#v", first)
	}
	sessionID, _ := first["session_id"].(string)
	client.Close()

	resumed := NewClient(nil)
	if err := resumed.Start(root, configPath, map[string]interface{}{"engine": "go"}); err != nil {
		t.Fatal(err)
	}
	defer resumed.Close()
	var resumeReply map[string]any
	if err := resumed.Call("agent.resume_session", map[string]interface{}{"identifier": sessionID}, &resumeReply); err != nil {
		t.Fatal(err)
	}
	var second map[string]any
	if err := resumed.Call("agent.run", map[string]interface{}{"user_input": "lanjut"}, &second); err != nil {
		t.Fatal(err)
	}
	if second["content"] != "siap" || len(requests) != 2 {
		t.Fatalf("unexpected second response=%#v requests=%d", second, len(requests))
	}
	messages, _ := requests[1]["messages"].([]any)
	encoded, _ := json.Marshal(messages)
	if !bytes.Contains(encoded, []byte("halo")) || !bytes.Contains(encoded, []byte("lanjut")) {
		t.Fatalf("resumed request omitted history: %s", encoded)
	}
}

func TestGoRuntimeRetainsFailedPromptForNextTurn(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	var calls atomic.Int32
	var recoveredRequest map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/v1/chat/completions" {
			http.NotFound(w, request)
			return
		}
		if calls.Add(1) == 1 {
			w.WriteHeader(http.StatusServiceUnavailable)
			_, _ = w.Write([]byte("sementara gagal"))
			return
		}
		if err := json.NewDecoder(request.Body).Decode(&recoveredRequest); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"pulih\"},\"finish_reason\":\"stop\"}]}\n\ndata: [DONE]\n\n"))
	}))
	defer server.Close()

	configPath := filepath.Join(root, "config.yaml")
	cfg := config.Defaults()
	cfg.Auth.Mode = "local"
	cfg.Auth.LocalEndpoint = server.URL
	cfg.Cloudflare.PrimaryModel = "local-test"
	cfg.Cloudflare.SecondaryModel = ""
	cfg.Retry.MaxRetries = 0
	if err := config.Save(configPath, cfg); err != nil {
		t.Fatal(err)
	}

	client := NewClient(nil)
	if err := client.Start(root, configPath, map[string]interface{}{"engine": "go"}); err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	var first map[string]any
	if err := client.Call("agent.run", map[string]interface{}{"user_input": "prompt yang harus tetap ada"}, &first); err == nil {
		t.Fatal("expected first provider request to fail")
	}
	if client.localSession == "default" {
		t.Fatal("failed request must create a recoverable local session")
	}
	var second map[string]any
	if err := client.Call("agent.run", map[string]interface{}{"user_input": "lanjut sekarang"}, &second); err != nil {
		t.Fatal(err)
	}
	if second["content"] != "pulih" {
		t.Fatalf("unexpected recovered response: %#v", second)
	}
	serialized, err := json.Marshal(recoveredRequest["messages"])
	if err != nil {
		t.Fatal(err)
	}
	for _, expected := range []string{"prompt yang harus tetap ada", "lanjut sekarang"} {
		if !bytes.Contains(serialized, []byte(expected)) {
			t.Fatalf("recovered request omitted %q: %s", expected, serialized)
		}
	}
}

func TestLocalSessionSaveAndResume(t *testing.T) {
	root := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", filepath.Join(root, "config"))
	c := &Client{localRoot: root, localSession: "session-test", localSessionName: "default"}
	var saved map[string]any
	if err := c.callLocal("agent.save_session", map[string]interface{}{"name": "demo"}, &saved); err != nil {
		t.Fatal(err)
	}
	sessions, err := c.localSessionManager()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := sessions.Load("demo"); err != nil {
		t.Fatal(err)
	}
	if saved["session_name"] != "demo" {
		t.Fatalf("unexpected save response: %#v", saved)
	}
	var resumed map[string]any
	if err := c.callLocal("agent.resume_session", map[string]interface{}{"identifier": "demo"}, &resumed); err != nil {
		t.Fatal(err)
	}
	if resumed["session_id"] != saved["session_id"] || resumed["session_name"] != "demo" {
		raw, _ := json.Marshal(resumed)
		t.Fatalf("unexpected resume response: %s", raw)
	}
}

func TestCompactTailTurnsMatchesEnginePolicy(t *testing.T) {
	if got := compactTailTurns(1); got != 12 {
		t.Fatalf("compact tail = %d, want 12", got)
	}
}

func TestExportEmptySessionIsHelpful(t *testing.T) {
	root := t.TempDir()
	c := &Client{localRoot: root, localSession: "empty"}
	var reply map[string]any
	if err := c.callLocal("agent.run", map[string]interface{}{"user_input": "/export"}, &reply); err != nil {
		t.Fatal(err)
	}
	if reply["content"] != "Belum ada percakapan untuk diekspor." {
		t.Fatalf("unexpected export response: %#v", reply)
	}
}

func TestCopyableSessionMessage(t *testing.T) {
	messages := []model.Message{{Role: "system", Content: "internal"}, {Role: "user", Content: "satu"}, {Role: "tool", Content: "hidden"}, {Role: "assistant", Content: "dua"}}
	last, err := copyableSessionMessage(messages, "last")
	if err != nil || last != "dua" {
		t.Fatalf("unexpected last message: %q err=%v", last, err)
	}
	first, err := copyableSessionMessage(messages, "1")
	if err != nil || first != "satu" {
		t.Fatalf("unexpected selected message: %q err=%v", first, err)
	}
}

func TestProjectCommandBuildsNativeProject(t *testing.T) {
	c := &Client{localRoot: t.TempDir()}
	if output, err := c.projectCommand("new demo"); err != nil || output == "" {
		t.Fatalf("new project failed: %q err=%v", output, err)
	}
	if output, err := c.projectCommand("add reviewer periksa struktur proyek"); err != nil || output == "" {
		t.Fatalf("add worker failed: %q err=%v", output, err)
	}
	if output, err := c.projectCommand("add deploy rilis proyek"); err != nil || output == "" {
		t.Fatalf("add dependent worker failed: %q err=%v", output, err)
	}
	if output, err := c.projectCommand("depends deploy reviewer"); err != nil || !strings.Contains(output, "reviewer") {
		t.Fatalf("dependency command failed: %q err=%v", output, err)
	}
	output, err := c.projectCommand("status")
	if err != nil || !strings.Contains(output, "reviewer [pending]") || !strings.Contains(output, "after:reviewer") {
		t.Fatalf("unexpected status: %q err=%v", output, err)
	}
	if output, err := c.projectCommand("pause"); err != nil || !strings.Contains(output, "dijeda") {
		t.Fatalf("pause command failed: %q err=%v", output, err)
	}
}

func TestAgentStatusOnlyTicksProjectAfterSchedulerIsStarted(t *testing.T) {
	c := &Client{localRoot: t.TempDir()}
	if _, err := c.projectCommand("new demo"); err != nil {
		t.Fatal(err)
	}
	if _, err := c.projectCommand("add reviewer periksa proyek"); err != nil {
		t.Fatal(err)
	}
	c.localGhosts.MaxAgents = 0
	var status map[string]any
	if err := c.callLocal("agent.status", map[string]interface{}{}, &status); err != nil {
		t.Fatal(err)
	}
	if c.localProjects.Active().SchedulerEnabled {
		t.Fatal("status polling must not start a new project scheduler")
	}
	if _, err := c.projectCommand("run"); err != nil {
		t.Fatal(err)
	}
	if !c.localProjects.Active().SchedulerEnabled {
		t.Fatal("project run must enable persistent scheduling")
	}
	if err := c.callLocal("agent.status", map[string]interface{}{}, &status); err != nil {
		t.Fatal(err)
	}
}

func TestAgentStatusDoesNotErrorWithoutAnActiveProject(t *testing.T) {
	c := &Client{
		localRoot:     t.TempDir(),
		localProjects: projectstore.NewManager(),
		localGhosts:   ghost.NewGhostManager(t.TempDir()),
	}
	var status map[string]any
	if err := c.callLocal("agent.status", map[string]interface{}{}, &status); err != nil {
		t.Fatal(err)
	}
}

func TestNativeGenomeAndLoopCommands(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "main.go"), []byte("package main\nfunc main() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	c := &Client{localRoot: root, localConfig: config.Config{Cloudflare: config.Cloudflare{PrimaryModel: "primary", SecondaryModel: "secondary"}}}
	var reply map[string]any
	if handled, err := c.localSlash("/genome check", &reply); !handled || err != nil || !strings.Contains(reply["content"].(string), "Tidak ada duplicate") {
		t.Fatalf("genome command failed: handled=%v err=%v reply=%#v", handled, err, reply)
	}
	if handled, err := c.localSlash("/loop reset", &reply); !handled || err != nil || !strings.Contains(reply["content"].(string), "di-reset") {
		t.Fatalf("loop reset failed: handled=%v err=%v reply=%#v", handled, err, reply)
	}
	if handled, err := c.localSlash("/loop break", &reply); !handled || err != nil || c.localConfig.Cloudflare.PrimaryModel != "secondary" {
		t.Fatalf("loop break failed: handled=%v err=%v config=%#v", handled, err, c.localConfig.Cloudflare)
	}
}

func TestNativeProofSlashFlowSupportsTitlesWithSpaces(t *testing.T) {
	root := t.TempDir()
	for _, args := range [][]string{
		{"init"},
		{"config", "user.name", "Autokeren Test"},
		{"config", "user.email", "test@example.invalid"},
		{"commit", "--allow-empty", "-m", "initial"},
	} {
		command := exec.Command("git", append([]string{"-C", root}, args...)...)
		if output, err := command.CombinedOutput(); err != nil {
			t.Fatalf("git %s failed: %v\n%s", strings.Join(args, " "), err, output)
		}
	}
	c := &Client{localRoot: root}
	var reply map[string]any
	if handled, err := c.localSlash("/proof plan Shoe store release | Homepage loads | Tests pass", &reply); !handled || err != nil {
		t.Fatalf("proof plan failed: handled=%v err=%v", handled, err)
	}
	if !strings.Contains(reply["content"].(string), "Proof ID:") {
		t.Fatalf("proof plan did not return an ID: %#v", reply)
	}
	entries, err := os.ReadDir(filepath.Join(root, ".autokeren", "proofs"))
	if err != nil || len(entries) != 1 {
		t.Fatalf("expected one proof artifact: entries=%#v err=%v", entries, err)
	}
	proofID := strings.TrimSuffix(entries[0].Name(), ".json")
	for _, command := range []string{
		"/proof record " + proofID + " 1 passed | browser: PASS",
		"/proof record " + proofID + " 2 passed | go test ./...: PASS",
		"/proof approve " + proofID,
		"/proof report " + proofID,
	} {
		if handled, err := c.localSlash(command, &reply); !handled || err != nil {
			t.Fatalf("proof command %q failed: handled=%v err=%v", command, handled, err)
		}
	}
	if !strings.Contains(reply["content"].(string), "Approval: APPROVED") {
		t.Fatalf("approved proof report missing approval: %#v", reply)
	}
}

func TestSpecProgress(t *testing.T) {
	progress := specProgress("- [x] selesai\n- [ ] berikutnya")
	if progress != "Progress: 50% (1/2 langkah selesai)" {
		t.Fatalf("unexpected progress: %q", progress)
	}
}
