package tool

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCFVerifyHTTP(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { _, _ = w.Write([]byte("ok")) }))
	defer server.Close()
	result := (CFVerify{Root: t.TempDir()}).Run(context.Background(), map[string]any{"url": server.URL}, nil)
	if !result.OK {
		t.Fatalf("expected verification success: %v", result.Error)
	}
}
