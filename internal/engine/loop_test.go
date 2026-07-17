package engine

import (
	"context"
	"github.com/autokeren/autokeren/internal/model"
	"github.com/autokeren/autokeren/internal/provider"
	"github.com/autokeren/autokeren/internal/tool"
	"testing"
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
