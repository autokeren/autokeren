package provider

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"github.com/autokeren/autokeren/internal/model"
)

type scriptedResult struct {
	response model.Response
	err      error
	chunks   []string
}

type scriptedProvider struct {
	results []scriptedResult
	calls   int
}

func (p *scriptedProvider) Complete(_ context.Context, _ model.Request, onChunk ChunkHandler) (model.Response, error) {
	p.calls++
	index := p.calls - 1
	if index >= len(p.results) {
		return model.Response{}, errors.New("unexpected provider call")
	}
	result := p.results[index]
	for _, chunk := range result.chunks {
		if onChunk != nil {
			if err := onChunk(chunk); err != nil {
				return model.Response{}, err
			}
		}
	}
	return result.response, result.err
}

func newTestRouter(t *testing.T, targets []Target, retry RetryPolicy, state *RouterState, events *[]RetryEvent) *Router {
	t.Helper()
	router, err := NewRouter(RouterConfig{
		Targets:                 targets,
		Retry:                   retry,
		CircuitFailureThreshold: 1,
		CircuitOpenDuration:     time.Minute,
		State:                   state,
		OnRetry: func(event RetryEvent) {
			*events = append(*events, event)
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	router.sleep = func(context.Context, time.Duration) error { return nil }
	router.random = func() float64 { return 0.5 }
	return router
}

func TestRouterRetriesRetriableError(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{
		{err: &Error{Status: 503, Cause: errors.New("temporary unavailable")}},
		{response: model.Response{Content: "siap"}},
	}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}}, RetryPolicy{MaxRetries: 1}, nil, &events)

	response, err := router.Complete(context.Background(), model.Request{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "siap" || response.Model != "primary" {
		t.Fatalf("unexpected response: %#v", response)
	}
	if primary.calls != 2 || len(events) != 1 || events[0].Attempt != 1 {
		t.Fatalf("calls=%d events=%#v", primary.calls, events)
	}
}

func TestRouterRetriesProviderTransportTimeout(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{
		{err: &Error{Cause: context.DeadlineExceeded}},
		{response: model.Response{Content: "pulih setelah timeout"}},
	}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}}, RetryPolicy{MaxRetries: 1}, nil, &events)

	response, err := router.Complete(context.Background(), model.Request{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "pulih setelah timeout" || primary.calls != 2 {
		t.Fatalf("response=%#v calls=%d", response, primary.calls)
	}
	if len(events) != 1 || events[0].Attempt != 1 {
		t.Fatalf("expected one retry event, got %#v", events)
	}
}

func TestRouterRetriesHTTPClientTimeout(t *testing.T) {
	var calls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		if calls.Add(1) == 1 {
			time.Sleep(75 * time.Millisecond)
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"pulih\"},\"finish_reason\":\"stop\"}]}\n\ndata: [DONE]\n\n"))
	}))
	defer server.Close()

	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{
		ModelID:  "primary",
		Provider: OpenAICompatible{Endpoint: server.URL, Client: &http.Client{Timeout: 15 * time.Millisecond}},
	}}, RetryPolicy{MaxRetries: 1}, nil, &events)

	response, err := router.Complete(context.Background(), model.Request{Messages: []model.Message{{Role: "user", Content: "halo"}}}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "pulih" || calls.Load() != 2 {
		t.Fatalf("response=%#v calls=%d", response, calls.Load())
	}
	if len(events) != 1 || events[0].Attempt != 1 {
		t.Fatalf("expected one retry event, got %#v", events)
	}
}

func TestRouterFallsBackAfterProviderTransportTimeout(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{{err: &Error{Cause: context.DeadlineExceeded}}}}
	secondary := &scriptedProvider{results: []scriptedResult{{response: model.Response{Content: "fallback setelah timeout"}}}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}, {ModelID: "secondary", Provider: secondary}}, RetryPolicy{}, nil, &events)

	response, err := router.Complete(context.Background(), model.Request{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "fallback setelah timeout" || primary.calls != 1 || secondary.calls != 1 {
		t.Fatalf("response=%#v primary=%d secondary=%d", response, primary.calls, secondary.calls)
	}
	if len(events) != 1 || events[0].Attempt != 0 {
		t.Fatalf("expected fallback event, got %#v", events)
	}
}

func TestRouterStopsForCallerDeadline(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{{err: &Error{Cause: context.DeadlineExceeded}}}}
	secondary := &scriptedProvider{results: []scriptedResult{{response: model.Response{Content: "must not run"}}}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}, {ModelID: "secondary", Provider: secondary}}, RetryPolicy{MaxRetries: 1}, nil, &events)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	_, err := router.Complete(ctx, model.Request{}, nil)
	if !errors.Is(err, context.DeadlineExceeded) || primary.calls != 1 || secondary.calls != 0 || len(events) != 0 {
		t.Fatalf("err=%v primary=%d secondary=%d events=%#v", err, primary.calls, secondary.calls, events)
	}
}

func TestRouterFallsBackAfterPrimaryFailure(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{{err: &Error{Status: 503, Cause: errors.New("primary unavailable")}}}}
	secondary := &scriptedProvider{results: []scriptedResult{{response: model.Response{Content: "secondary"}}}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}, {ModelID: "secondary", Provider: secondary}}, RetryPolicy{}, nil, &events)

	response, err := router.Complete(context.Background(), model.Request{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "secondary" || response.Model != "secondary" {
		t.Fatalf("unexpected fallback response: %#v", response)
	}
	if primary.calls != 1 || secondary.calls != 1 || len(events) != 1 || events[0].Attempt != 0 {
		t.Fatalf("primary=%d secondary=%d events=%#v", primary.calls, secondary.calls, events)
	}
}

func TestRouterPrefersFallbackAfterMalformedToolCall(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{{response: model.Response{Content: "primary should not run"}}}}
	secondary := &scriptedProvider{results: []scriptedResult{{response: model.Response{Content: "secondary repair"}}}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}, {ModelID: "secondary", Provider: secondary}}, RetryPolicy{}, nil, &events)
	router.PreferFallbackAfter("primary")

	response, err := router.Complete(context.Background(), model.Request{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "secondary repair" || response.Model != "secondary" || primary.calls != 0 || secondary.calls != 1 {
		t.Fatalf("response=%#v primary=%d secondary=%d", response, primary.calls, secondary.calls)
	}
}

func TestRouterSharesCircuitStateAcrossTurns(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{{err: &Error{Status: 503, Cause: errors.New("primary unavailable")}}}}
	secondary := &scriptedProvider{results: []scriptedResult{{response: model.Response{Content: "fallback one"}}, {response: model.Response{Content: "fallback two"}}}}
	state := NewRouterState()
	events := []RetryEvent{}
	targets := []Target{{ModelID: "primary", Provider: primary}, {ModelID: "secondary", Provider: secondary}}

	first := newTestRouter(t, targets, RetryPolicy{}, state, &events)
	if _, err := first.Complete(context.Background(), model.Request{}, nil); err != nil {
		t.Fatal(err)
	}
	second := newTestRouter(t, targets, RetryPolicy{}, state, &events)
	response, err := second.Complete(context.Background(), model.Request{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "fallback two" || primary.calls != 1 || secondary.calls != 2 {
		t.Fatalf("response=%#v primary=%d secondary=%d", response, primary.calls, secondary.calls)
	}
	status := state.Status()["primary"]
	if status.State != "open" {
		t.Fatalf("unexpected circuit status: %#v", status)
	}
}

func TestRouterDoesNotReplayStartedStream(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{{chunks: []string{"partial"}, err: &Error{Cause: errors.New("stream disconnected")}}}}
	secondary := &scriptedProvider{results: []scriptedResult{{response: model.Response{Content: "must not run"}}}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}, {ModelID: "secondary", Provider: secondary}}, RetryPolicy{MaxRetries: 3}, nil, &events)

	_, err := router.Complete(context.Background(), model.Request{}, func(string) error { return nil })
	if err == nil || !StreamStarted(err) {
		t.Fatalf("expected started stream error, got %v", err)
	}
	if primary.calls != 1 || secondary.calls != 0 || len(events) != 0 {
		t.Fatalf("primary=%d secondary=%d events=%#v", primary.calls, secondary.calls, events)
	}
}

func TestRouterDoesNotFallbackContextLimit(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{{err: &Error{Status: 400, Cause: errors.New("provider code 8007 context length exceeded")}}}}
	secondary := &scriptedProvider{results: []scriptedResult{{response: model.Response{Content: "must not run"}}}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}, {ModelID: "secondary", Provider: secondary}}, RetryPolicy{MaxRetries: 3}, nil, &events)

	_, err := router.Complete(context.Background(), model.Request{}, nil)
	if err == nil || primary.calls != 1 || secondary.calls != 0 || len(events) != 0 {
		t.Fatalf("err=%v primary=%d secondary=%d events=%#v", err, primary.calls, secondary.calls, events)
	}
}

func TestIsContextLimitRecognizesCommonProviderMessages(t *testing.T) {
	for _, message := range []string{
		"request exceeds the context window",
		"context limit reached",
		"provider code 8007: context length exceeded",
	} {
		if !IsContextLimit(errors.New(message)) {
			t.Fatalf("context limit not recognized: %q", message)
		}
	}
	if IsContextLimit(errors.New("8007: Assistant tool call function.arguments must be valid JSON")) {
		t.Fatal("tool call JSON error tidak boleh dianggap context limit")
	}
}

func TestRouterHonorsRetryAfter(t *testing.T) {
	primary := &scriptedProvider{results: []scriptedResult{
		{err: &Error{Status: 429, RetryAfter: 2 * time.Second, Cause: errors.New("rate limited")}},
		{response: model.Response{Content: "recovered"}},
	}}
	events := []RetryEvent{}
	router := newTestRouter(t, []Target{{ModelID: "primary", Provider: primary}}, RetryPolicy{MaxRetries: 1, MaxDelay: 5 * time.Second}, nil, &events)
	var waited time.Duration
	router.sleep = func(_ context.Context, delay time.Duration) error {
		waited = delay
		return nil
	}

	response, err := router.Complete(context.Background(), model.Request{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "recovered" || waited != 2*time.Second || len(events) != 1 || events[0].Delay != 2*time.Second {
		t.Fatalf("response=%#v waited=%s events=%#v", response, waited, events)
	}
}
