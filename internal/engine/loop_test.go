package engine

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/autokeren/autokeren/internal/checkpoint"
	contextstore "github.com/autokeren/autokeren/internal/context"
	"github.com/autokeren/autokeren/internal/model"
	"github.com/autokeren/autokeren/internal/provider"
	"github.com/autokeren/autokeren/internal/tool"
	"strings"
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

type writeFileProvider struct{ calls int }

func (p *writeFileProvider) Complete(_ context.Context, _ model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	if p.calls == 1 {
		return model.Response{ToolCalls: []model.ToolCall{{ID: "write", Type: "function", Function: model.ToolCallFunction{Name: "write_file", Arguments: `{"path":"created.txt","content":"checkpointed"}`}}}}, nil
	}
	return model.Response{Content: "selesai"}, nil
}

func TestLoopCheckpointsWriteAndRewindRestoresDisk(t *testing.T) {
	root := t.TempDir()
	manager, err := checkpoint.New(root, "default", 50, true)
	if err != nil {
		t.Fatal(err)
	}
	loop := &Loop{Runner: Runner{Provider: &writeFileProvider{}}, Tools: tool.NewRegistry().Register(tool.WriteFile{Root: root}), MaxIterations: 3, Checkpoints: manager}
	if _, err := loop.Run(context.Background(), "buat file", Events{}); err != nil {
		t.Fatal(err)
	}
	if data, err := os.ReadFile(filepath.Join(root, "created.txt")); err != nil || string(data) != "checkpointed" || manager.Count() != 1 {
		t.Fatalf("write/checkpoint gagal: data=%q err=%v checkpoints=%d", data, err, manager.Count())
	}
	if result := (tool.Rewind{Manager: manager}).Run(context.Background(), map[string]any{"steps": float64(1)}, nil); !result.OK {
		t.Fatal(result.Error)
	}
	if _, err := os.Stat(filepath.Join(root, "created.txt")); !os.IsNotExist(err) {
		t.Fatalf("rewind loop tidak memulihkan disk: %v", err)
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

type autonomousContinuationProvider struct{ calls int }

func (p *autonomousContinuationProvider) Complete(_ context.Context, _ model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	switch p.calls {
	case 1:
		return model.Response{ToolCalls: []model.ToolCall{{ID: "1", Type: "function", Function: model.ToolCallFunction{Name: "echo", Arguments: `{"value":"ok"}`}}}}, nil
	case 2:
		return model.Response{Content: "Selanjutnya akan saya lanjutkan verifikasinya."}, nil
	default:
		return model.Response{Content: "Selesai, verifikasi sudah tuntas."}, nil
	}
}

func TestLoopContinuesOneAutonomousTurnAfterToolWork(t *testing.T) {
	p := &autonomousContinuationProvider{}
	continuations := 0
	loop := &Loop{Runner: Runner{Provider: p}, Tools: tool.NewRegistry().Register(echoTool{}), MaxIterations: 4}
	response, err := loop.Run(context.Background(), "selesaikan tugas", Events{OnRetry: func(int, time.Duration, string) { continuations++ }})
	if err != nil || response.Content != "Selesai, verifikasi sudah tuntas." || p.calls != 3 || continuations != 1 {
		t.Fatalf("response=%#v err=%v calls=%d continuations=%d", response, err, p.calls, continuations)
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

type backgroundSpawnTool struct{}

func (backgroundSpawnTool) Definition() tool.Definition {
	return tool.Definition{Name: "spawn_agent", Parameters: map[string]any{"type": "object"}}
}
func (backgroundSpawnTool) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (backgroundSpawnTool) Run(context.Context, map[string]any, tool.Emitter) tool.Result {
	return tool.Result{OK: true, Output: "ghost #7 started"}
}

type awaitAgentsTool struct {
	calls     int
	monitored []int
}

func (a *awaitAgentsTool) Definition() tool.Definition {
	return tool.Definition{Name: "await_agents", Parameters: map[string]any{"type": "object"}}
}
func (a *awaitAgentsTool) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (a *awaitAgentsTool) Run(_ context.Context, args map[string]any, _ tool.Emitter) tool.Result {
	a.calls++
	ids, _ := args["agent_ids"].([]any)
	if len(ids) != 1 || ids[0] != float64(7) {
		return tool.Result{OK: false, Error: "worker ID salah"}
	}
	return tool.Result{OK: true, Output: `{"entries":[{"agent_id":7,"status":"completed","output":"worker selesai"}]}`}
}

func (a *awaitAgentsTool) MonitorBackground(ids []int) { a.monitored = append(a.monitored, ids...) }

type directorProvider struct{ calls int }

func (p *directorProvider) Complete(_ context.Context, request model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	if p.calls == 1 {
		return model.Response{ToolCalls: []model.ToolCall{{ID: "spawn", Type: "function", Function: model.ToolCallFunction{Name: "spawn_agent", Arguments: `{"task":"cek","background":true}`}}}}, nil
	}
	return model.Response{Content: "director lanjut tanpa menunggu worker"}, nil
}

func TestLoopDoesNotWaitForBackgroundWorkerUnlessRequested(t *testing.T) {
	awaiting := &awaitAgentsTool{}
	registry := tool.NewRegistry().Register(backgroundSpawnTool{}).Register(awaiting)
	p := &directorProvider{}
	loop := &Loop{Runner: Runner{Provider: p}, Tools: registry, MaxIterations: 3}
	response, err := loop.Run(context.Background(), "delegasikan", Events{})
	if err != nil || response.Content != "director lanjut tanpa menunggu worker" || awaiting.calls != 0 || p.calls != 2 || len(awaiting.monitored) != 1 || awaiting.monitored[0] != 7 {
		t.Fatalf("response=%#v err=%v awaits=%d monitored=%v provider_calls=%d", response, err, awaiting.calls, awaiting.monitored, p.calls)
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

type invalidToolArgumentsProvider struct {
	calls          int
	recoveryPrompt bool
	invalidLeaked  bool
	toolRetried    bool
}

func (p *invalidToolArgumentsProvider) Complete(_ context.Context, request model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	switch p.calls {
	case 1:
		return model.Response{ToolCalls: []model.ToolCall{{ID: "bad", Type: "function", Function: model.ToolCallFunction{Name: "echo", Arguments: `{"value":"first"}{"value":"second"}`}}}}, nil
	case 2:
		for _, message := range request.Messages {
			if message.Role == "assistant" && len(message.ToolCalls) > 0 {
				p.invalidLeaked = true
			}
			if message.Role == "system" && strings.Contains(message.Content, "format argumennya rusak") {
				p.recoveryPrompt = true
			}
		}
		return model.Response{ToolCalls: []model.ToolCall{{ID: "retry", Type: "function", Function: model.ToolCallFunction{Name: "echo", Arguments: `{"value":"recovered"}`}}}}, nil
	default:
		for _, message := range request.Messages {
			if message.Role == "tool" && message.Name == "echo" && strings.Contains(message.Content, "recovered") {
				p.toolRetried = true
			}
		}
		return model.Response{Content: "argumen diperbaiki"}, nil
	}
}

func TestLoopRecoversMalformedToolArgumentsWithoutForwardingInvalidJSON(t *testing.T) {
	p := &invalidToolArgumentsProvider{}
	loop := &Loop{Runner: Runner{Provider: p}, Tools: tool.NewRegistry().Register(echoTool{}), MaxIterations: 4}
	response, err := loop.Run(context.Background(), "coba tool", Events{})
	if err != nil || response.Content != "argumen diperbaiki" || p.calls != 3 || !p.recoveryPrompt || p.invalidLeaked || !p.toolRetried {
		t.Fatalf("response=%#v err=%v calls=%d recovery=%t leaked=%t retried=%t", response, err, p.calls, p.recoveryPrompt, p.invalidLeaked, p.toolRetried)
	}
}

type poisonedSessionProvider struct {
	calls         int
	recoverySeen  bool
	invalidLeaked bool
	orphanLeaked  bool
}

func (p *poisonedSessionProvider) Complete(_ context.Context, request model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	knownCalls := map[string]struct{}{}
	for _, message := range request.Messages {
		if message.Role == "assistant" {
			for _, call := range message.ToolCalls {
				knownCalls[call.ID] = struct{}{}
				if !json.Valid([]byte(call.Function.Arguments)) {
					p.invalidLeaked = true
				}
			}
		}
		if message.Role == "tool" {
			if _, ok := knownCalls[message.ToolCallID]; !ok {
				p.orphanLeaked = true
			}
		}
		if message.Role == "system" && strings.Contains(message.Content, "Riwayat") && strings.Contains(message.Content, "dibersihkan") {
			p.recoverySeen = true
		}
	}
	return model.Response{Content: "sesi lama pulih"}, nil
}

func TestLoopCleansPoisonedResumedToolHistoryBeforeProviderRequest(t *testing.T) {
	store := contextstore.New(262144, false, 0.6)
	store.Replace([]model.Message{
		{Role: "system", Content: "aturan"},
		{Role: "user", Content: "permintaan lama"},
		{Role: "assistant", ToolCalls: []model.ToolCall{{ID: "broken", Type: "function", Function: model.ToolCallFunction{Name: "run_shell", Arguments: `{"command":"pwd"`}}}},
		{Role: "tool", Name: "run_shell", ToolCallID: "broken", Content: "argumen tool tidak valid"},
	})
	p := &poisonedSessionProvider{}
	loop := &Loop{Runner: Runner{Provider: p}, Context: store, MaxIterations: 2}
	response, err := loop.Run(context.Background(), "lanjut", Events{})
	if err != nil || response.Content != "sesi lama pulih" || p.calls != 1 || !p.recoverySeen || p.invalidLeaked || p.orphanLeaked {
		t.Fatalf("poisoned session tidak dibersihkan: response=%#v err=%v calls=%d recovery=%t invalid=%t orphan=%t", response, err, p.calls, p.recoverySeen, p.invalidLeaked, p.orphanLeaked)
	}
}

func TestSanitizeToolHistoryPreservesCompletedValidToolCalls(t *testing.T) {
	valid := model.ToolCall{ID: "valid", Type: "function", Function: model.ToolCallFunction{Name: "echo", Arguments: `{"value":"ok"}`}}
	cleaned, removed := sanitizeToolHistory([]model.Message{
		{Role: "assistant", ToolCalls: []model.ToolCall{valid}},
		{Role: "tool", Name: "echo", ToolCallID: "valid", Content: `{"ok":true}`},
	})
	if removed != 0 || len(cleaned) != 2 || len(cleaned[0].ToolCalls) != 1 || cleaned[1].ToolCallID != "valid" {
		t.Fatalf("tool history valid berubah: cleaned=%#v removed=%d", cleaned, removed)
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

type contextLimitTwiceThenSuccessProvider struct {
	calls     int
	compacted bool
}

func (p *contextLimitTwiceThenSuccessProvider) Complete(_ context.Context, request model.Request, _ provider.ChunkHandler) (model.Response, error) {
	p.calls++
	if p.calls <= 2 {
		return model.Response{}, &provider.Error{Status: 400, Cause: errors.New("request exceeds the context window")}
	}
	for _, message := range request.Messages {
		if message.Role == "system" && strings.Contains(message.Content, "Ringkasan context lama") {
			p.compacted = true
		}
	}
	return model.Response{Content: "pulih setelah compact kedua"}, nil
}

func TestLoopRetriesMultipleContextLimitRecoveries(t *testing.T) {
	store := contextstore.New(262144, false, 0.6)
	store.SetCompactTail(1)
	store.Replace([]model.Message{
		{Role: "system", Content: "rules"},
		{Role: "user", Content: "old task"},
		{Role: "assistant", Content: "old answer"},
		{Role: "user", Content: "older task"},
		{Role: "assistant", Content: "older answer"},
	})
	p := &contextLimitTwiceThenSuccessProvider{}
	retries := 0
	loop := &Loop{Runner: Runner{Provider: p}, Context: store, MaxIterations: 4}
	response, err := loop.Run(context.Background(), "current task", Events{OnRetry: func(int, time.Duration, string) { retries++ }})
	if err != nil || response.Content != "pulih setelah compact kedua" || p.calls != 3 || !p.compacted || retries != 2 {
		t.Fatalf("response=%#v err=%v calls=%d compacted=%t retries=%d", response, err, p.calls, p.compacted, retries)
	}
}
