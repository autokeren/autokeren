package ipc

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/autokeren/autokeren/internal/config"
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
