package fddm

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestSniffContextUsesBoundedRedactedPayload(t *testing.T) {
	secret := "sk-live-abcdefghijklmno"
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/api/sniff_text" {
			t.Fatalf("path = %s", request.URL.Path)
		}
		if request.Header.Get("Authorization") != "Bearer test-key" {
			t.Fatalf("authorization = %q", request.Header.Get("Authorization"))
		}
		var payload map[string]any
		if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		if text, _ := payload["text"].(string); strings.Contains(text, secret) {
			t.Fatalf("secret bocor ke FDDM: %q", text)
		}
		if payload["top_k"] != float64(3) || payload["radius"] != 0.2 {
			t.Fatalf("payload sniff = %#v", payload)
		}
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`[{"type":"decision","score":0.9,"artifact":"gunakan retry aman"}]`))
	}))
	defer server.Close()
	client := New(Config{URL: server.URL, APIKey: "test-key"}, nil)
	contextText, err := client.SniffContext(context.Background(), "cek api_key="+secret)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(contextText, "FDDM AUTO-SNIFF") || !strings.Contains(contextText, "gunakan retry aman") {
		t.Fatalf("context FDDM = %q", contextText)
	}
}

func TestEmitCompletionIsShortCircuitAndRedacted(t *testing.T) {
	calls := 0
	secret := "sk-live-abcdefghijklmno"
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		calls++
		if request.URL.Path != "/api/emit_text" {
			t.Fatalf("path = %s", request.URL.Path)
		}
		var payload map[string]any
		if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		text, _ := payload["text"].(string)
		if strings.Contains(text, secret) || payload["base_score"] != 0.6 {
			t.Fatalf("payload emit = %#v", payload)
		}
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`{"scent_id":"ok"}`))
	}))
	defer server.Close()
	client := New(Config{URL: server.URL}, nil)
	if err := client.EmitCompletion(context.Background(), "api_key="+secret, "pendek"); err != nil {
		t.Fatal(err)
	}
	if calls != 0 {
		t.Fatalf("emit pendek tidak boleh request, calls=%d", calls)
	}
	if err := client.EmitCompletion(context.Background(), "api_key="+secret, "hasil yang cukup panjang untuk melewati batas emit otomatis"); err != nil {
		t.Fatal(err)
	}
	if calls != 1 {
		t.Fatalf("emit completion calls=%d, want 1", calls)
	}
}

func TestRequestHonorsTimeout(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		time.Sleep(100 * time.Millisecond)
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`[]`))
	}))
	defer server.Close()
	client := New(Config{URL: server.URL, Timeout: 20 * time.Millisecond}, nil)
	started := time.Now()
	_, err := client.Sniff(context.Background(), "test", 3, 0.2)
	if err == nil || time.Since(started) > time.Second {
		t.Fatalf("timeout FDDM tidak berlaku: err=%v elapsed=%s", err, time.Since(started))
	}
}

func TestDisabledClientMakesNoRequest(t *testing.T) {
	client := New(Config{}, nil)
	if _, err := client.Sniff(context.Background(), "test", 3, 0.2); err == nil {
		t.Fatal("FDDM tanpa URL harus nonaktif")
	}
}
