package ipc

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"github.com/autokeren/autokeren/internal/config"
	"github.com/autokeren/autokeren/internal/model"
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
	output, err := c.projectCommand("status")
	if err != nil || !strings.Contains(output, "reviewer [pending]") {
		t.Fatalf("unexpected status: %q err=%v", output, err)
	}
}

func TestSpecProgress(t *testing.T) {
	progress := specProgress("- [x] selesai\n- [ ] berikutnya")
	if progress != "Progress: 50% (1/2 langkah selesai)" {
		t.Fatalf("unexpected progress: %q", progress)
	}
}
