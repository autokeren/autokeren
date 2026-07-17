package engine

import (
	"context"
	"errors"
	contextstore "github.com/autokeren/autokeren/internal/context"
	"github.com/autokeren/autokeren/internal/model"
	"github.com/autokeren/autokeren/internal/provider"
	"github.com/autokeren/autokeren/internal/tool"
	"strings"
	"testing"
	"time"
)

type fakeProvider struct{ calls int }

func (p *fakeProvider) Complete(_ context.Context, _ model.Request, onChunk provider.ChunkHandler) (model.Response, error) {
	p.calls++
	if p.calls == 1 {
		return model.Response{ToolCalls: []model.ToolCall{{ID: "1", Type: "function", Function: model.ToolCallFunction{Name: "echo", Arguments: `{"value":"ok"}`}}}}, nil
	}
	if onChunk != nil {
		_ = onChunk("done")
	}
	return model.Response{Content: "finished"}, nil
}

type echoTool struct{}

func (echoTool) Definition() tool.Definition {
	return tool.Definition{Name: "echo", Description: "echo", Parameters: map[string]any{"type": "object"}}
}
func (echoTool) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (echoTool) Run(_ context.Context, args map[string]any, _ tool.Emitter) tool.Result {
	return tool.Result{OK: true, Output: args["value"]}
}
func TestLoopDispatchesToolAndContinues(t *testing.T) {
	registry := tool.NewRegistry().Register(echoTool{})
	p := &fakeProvider{}
	loop := &Loop{Runner: Runner{Provider: p}, Tools: registry, MaxIterations: 3}
	response, err := loop.Run(context.Background(), "hello", Events{})
	if err != nil {
		t.Fatal(err)
	}
	if response.Content != "finished" || p.calls != 2 {
		t.Fatalf("unexpected response %#v calls=%d", response, p.calls)
	}
}

type contentAndToolProvider struct{ calls int }

func (p *contentAndToolProvider) Complete(_ context.Context, _ model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	if p.calls == 1 {
		return model.Response{Content: "Saya mulai dulu.", ToolCalls: []model.ToolCall{{ID: "1", Type: "function", Function: model.ToolCallFunction{Name: "echo", Arguments: `{"value":"ok"}`}}}}, nil
	}
	return model.Response{Content: "Selesai."}, nil
}

func TestLoopDoesNotStopWhenContentAndToolCallsCoexist(t *testing.T) {
	registry := tool.NewRegistry().Register(echoTool{})
	p := &contentAndToolProvider{}
	loop := &Loop{Runner: Runner{Provider: p}, Tools: registry, MaxIterations: 3}
	response, err := loop.Run(context.Background(), "hello", Events{})
	if err != nil || response.Content != "Selesai." || p.calls != 2 {
		t.Fatalf("loop stopped before tool dispatch: response=%#v err=%v calls=%d", response, err, p.calls)
	}
}

func TestLoopPlanModeBlocksToolDispatch(t *testing.T) {
	registry := tool.NewRegistry().Register(echoTool{})
	p := &contentAndToolProvider{}
	loop := &Loop{Runner: Runner{Provider: p}, Tools: registry, MaxIterations: 3, PlanMode: true}
	response, err := loop.Run(context.Background(), "ubah file", Events{})
	if err != nil || response.Content != "Saya mulai dulu." || p.calls != 1 {
		t.Fatalf("plan mode should return plan without dispatch: response=%#v err=%v calls=%d", response, err, p.calls)
	}
	for _, message := range loop.Context.Messages() {
		if message.Role == "tool" {
			t.Fatalf("plan mode dispatched a tool: %#v", message)
		}
	}
}

type emptyThenContentProvider struct{ calls int }

func (p *emptyThenContentProvider) Complete(_ context.Context, _ model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	if p.calls == 1 {
		return model.Response{}, nil
	}
	return model.Response{Content: "pulih"}, nil
}

func TestLoopRetriesEmptyTerminalTurn(t *testing.T) {
	p := &emptyThenContentProvider{}
	loop := &Loop{Runner: Runner{Provider: p}, MaxIterations: 3}
	response, err := loop.Run(context.Background(), "hello", Events{})
	if err != nil || response.Content != "pulih" || p.calls != 2 {
		t.Fatalf("empty turn ended session: response=%#v err=%v calls=%d", response, err, p.calls)
	}
}

type waitingProvider struct{}

func (waitingProvider) Complete(ctx context.Context, _ model.Request, _ provider.ChunkHandler) (model.Response, error) {
	<-ctx.Done()
	return model.Response{}, ctx.Err()
}

func TestLoopRespectsCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	loop := &Loop{Runner: Runner{Provider: waitingProvider{}}, MaxIterations: 1}
	_, err := loop.Run(ctx, "hello", Events{})
	if err == nil || err != context.Canceled {
		t.Fatalf("expected cancellation, got %v", err)
	}
}

func TestWithCurrentSystemPromptReplacesLegacyPrompt(t *testing.T) {
	messages := withCurrentSystemPrompt([]model.Message{{Role: "system", Content: "legacy"}, {Role: "user", Content: "halo"}})
	if messages[0].Content != fallbackSystemPrompt || messages[1].Content != "halo" {
		t.Fatalf("unexpected messages: %#v", messages)
	}
}

type contextLimitThenSuccessProvider struct {
	calls     int
	compacted bool
}

func (p *contextLimitThenSuccessProvider) Complete(_ context.Context, request model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	if p.calls == 1 {
		return model.Response{}, &provider.Error{Status: 400, Cause: errors.New("provider code 8007 context length exceeded")}
	}
	for _, message := range request.Messages {
		if message.Role == "system" && strings.Contains(message.Content, "Ringkasan context lama") {
			p.compacted = true
		}
	}
	return model.Response{Content: "pulih"}, nil
}

func TestLoopCompactsAndRetriesContextLimitOnce(t *testing.T) {
	store := contextstore.New(262144, false, 0.6)
	store.SetCompactTail(1)
	store.Replace([]model.Message{
		{Role: "system", Content: "rules"},
		{Role: "user", Content: "old task"},
		{Role: "assistant", Content: "old answer"},
	})
	p := &contextLimitThenSuccessProvider{}
	retries := 0
	loop := &Loop{Runner: Runner{Provider: p}, Context: store, MaxIterations: 3}
	response, err := loop.Run(context.Background(), "current task", Events{OnRetry: func(int, time.Duration, string) { retries++ }})
	if err != nil || response.Content != "pulih" || p.calls != 2 || !p.compacted || retries != 1 {
		t.Fatalf("response=%#v err=%v calls=%d compacted=%t retries=%d", response, err, p.calls, p.compacted, retries)
	}
}
