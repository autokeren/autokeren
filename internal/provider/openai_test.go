package provider

import (
	"context"
	"errors"
	"github.com/autokeren/autokeren/internal/model"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestOpenAICompatibleStreaming(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test-key" {
			t.Errorf("missing auth header")
		}
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("X-Neurons-Used", "123")
		w.Header().Set("X-Neurons-Remaining", "9877")
		w.Header().Set("X-Neurons-Quota", "10000")
		_, _ = w.Write([]byte("data: {\"model\":\"test\",\"choices\":[{\"delta\":{\"content\":\"hello \"}}]}\n\n"))
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"world\"},\"finish_reason\":\"stop\"}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()
	var chunks []string
	response, err := (OpenAICompatible{Endpoint: server.URL, APIKey: "test-key"}).Complete(context.Background(), model.Request{Model: "test", Messages: []model.Message{{Role: "user", Content: "hi"}}}, func(chunk string) error { chunks = append(chunks, chunk); return nil })
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "hello world" {
		t.Fatalf("content = %q", response.Content)
	}
	if strings.Join(chunks, "") != "hello world" {
		t.Fatalf("chunks = %q", strings.Join(chunks, ""))
	}
	if response.Usage.NeuronsUsed != 123 || response.Usage.NeuronsRemaining != 9877 || response.Usage.NeuronsQuota != 10000 {
		t.Fatalf("unexpected neuron usage: %#v", response.Usage)
	}
}

func TestOpenAICompatibleReturnsTypedStatusError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Retry-After", "2")
		w.WriteHeader(http.StatusTooManyRequests)
		_, _ = w.Write([]byte("slow down"))
	}))
	defer server.Close()

	_, err := (OpenAICompatible{Endpoint: server.URL}).Complete(context.Background(), model.Request{Model: "test"}, nil)
	if err == nil {
		t.Fatal("expected provider error")
	}
	var providerErr *Error
	if !errors.As(err, &providerErr) {
		t.Fatalf("expected typed provider error, got %T", err)
	}
	if providerErr.Status != http.StatusTooManyRequests || providerErr.RetryAfter.Seconds() != 2 {
		t.Fatalf("unexpected provider error: %#v", providerErr)
	}
}
