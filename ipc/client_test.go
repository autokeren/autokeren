package ipc

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/autokeren/autokeren/internal/config"
	sessionstore "github.com/autokeren/autokeren/internal/session"
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
	c := &Client{localRoot: root, localSession: "session-test", localSessionName: "default"}
	var saved map[string]any
	if err := c.callLocal("agent.save_session", map[string]interface{}{"name": "demo"}, &saved); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(root, ".ak-sessions", "demo.json")); err != nil {
		t.Fatal(err)
	}
	if saved["session_name"] != "demo" {
		t.Fatalf("unexpected save response: %#v", saved)
	}
	var resumed map[string]any
	if err := c.callLocal("agent.resume_session", map[string]interface{}{"identifier": "demo"}, &resumed); err != nil {
		t.Fatal(err)
	}
	if resumed["session_id"] != "demo" {
		raw, _ := json.Marshal(resumed)
		t.Fatalf("unexpected resume response: %s", raw)
	}
}

func TestAutoSaveUsesPythonCompatibleNameAndUpdatesSession(t *testing.T) {
	root := t.TempDir()
	c := &Client{localRoot: root, localSession: "session-1", localSessionName: "default", localConfig: config.Config{Autokeren: config.Autokeren{AutoSaveSession: true}}}
	if err := sessionstore.Save(c.sessionPath(c.localSession), sessionstore.New(c.localSession, nil)); err != nil {
		t.Fatal(err)
	}
	if err := c.autoSaveLocalSession("Buat aplikasi kalender pintar"); err != nil {
		t.Fatal(err)
	}
	data, err := sessionstore.Load(c.sessionPath(c.localSession))
	if err != nil || data.Name == "" || data.Name == "default" {
		t.Fatalf("auto-save did not name session: %#v err=%v", data, err)
	}
}
