package engine

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/autokeren/autokeren/internal/checkpoint"
	contextstore "github.com/autokeren/autokeren/internal/context"
	"github.com/autokeren/autokeren/internal/model"
	"github.com/autokeren/autokeren/internal/provider"
	"github.com/autokeren/autokeren/internal/tool"
	"strings"
	"time"
)

type Events struct {
	OnChunk           func(string)
	OnRetry           func(int, time.Duration, string)
	OnToolStart       func(string, map[string]any)
	OnToolOutput      func(string, string)
	OnToolEnd         func(string, tool.Result)
	ConfirmPermission func(string, string, map[string]any) bool
	OnContextUpdated  func(int, int)
	OnResponse        func(model.Response)
	OnSessionSaved    func(string, string)
}

type Loop struct {
	Runner         Runner
	Tools          *tool.Registry
	Context        *contextstore.Store
	RequestPrelude []model.Message
	MaxIterations  int
	Model          string
	Temperature    float64
	MaxTokens      int
	PlanMode       bool
	Checkpoints    *checkpoint.Manager
}

const maxContextRecoveryAttempts = 3

func (l *Loop) Run(ctx context.Context, userInput string, events Events) (model.Response, error) {
	if l.Runner.Provider == nil {
		return model.Response{}, fmt.Errorf("agent provider is nil")
	}
	if l.Context == nil {
		l.Context = contextstore.New(262144, true, 0.6)
	}
	if l.Tools == nil {
		l.Tools = tool.NewRegistry()
	}
	l.Context.Add(model.Message{Role: "user", Content: userInput})
	l.emitContext(events)
	limit := l.MaxIterations
	if limit <= 0 {
		limit = 50
	}
	var last model.Response
	contextRecoveryAttempts := 0
	autonomousContinuationAttempts := 0
	for iteration := 0; iteration < limit; iteration++ {
		request := model.Request{Model: l.Model, Messages: mergeRequestMessages(l.Context.Messages(), l.RequestPrelude), Tools: definitions(l.Tools), Temperature: l.Temperature, MaxTokens: l.MaxTokens}
		var onChunk provider.ChunkHandler
		if events.OnChunk != nil {
			onChunk = func(chunk string) error { events.OnChunk(chunk); return nil }
		}
		last, err := l.Runner.RunTurn(ctx, request, onChunk)
		if err != nil {
			if provider.IsContextLimit(err) && contextRecoveryAttempts < maxContextRecoveryAttempts {
				before, after, changed := l.Context.Compact()
				if changed {
					contextRecoveryAttempts++
					if events.OnRetry != nil {
						events.OnRetry(contextRecoveryAttempts, 0, fmt.Sprintf("context penuh; compact otomatis %d → %d token lalu mencoba ulang", before, after))
					}
					l.emitContext(events)
					continue
				}
			}
			return model.Response{}, err
		}
		contextRecoveryAttempts = 0
		if len(last.ToolCalls) == 0 {
			l.Context.Add(model.Message{Role: "assistant", Content: last.Content})
			l.emitContext(events)
			if strings.TrimSpace(last.Content) == "" {
				// Providers can occasionally emit an empty terminal SSE turn. Give
				// the model another turn instead of silently ending the session.
				continue
			}
			if hasToolResults(l.Context.Messages()) && autonomousContinuationAttempts < 1 && iteration < limit-1 && shouldAutonomouslyContinue(last.Content) {
				autonomousContinuationAttempts++
				l.Context.Add(model.Message{Role: "system", Content: "KAMU SEDANG DALAM MODE OTONOM. Jangan sekadar menjelaskan langkah selanjutnya atau meminta maaf. Gunakan tool yang sesuai secara langsung untuk melanjutkan tugas sampai selesai sepenuhnya."})
				l.emitContext(events)
				if events.OnRetry != nil {
					events.OnRetry(0, 0, "agen menyatakan akan melanjutkan; meneruskan satu turn otonom")
				}
				continue
			}
			return last, nil
		}
		if l.PlanMode {
			content := strings.TrimSpace(last.Content)
			if content == "" {
				content = "Rencana memiliki aksi yang mengubah state. Tinjau rencana ini lalu jalankan /approve dan kirimkan perintah untuk melanjutkan."
			}
			l.Context.Add(model.Message{Role: "assistant", Content: content})
			return model.Response{Content: content, Model: last.Model, Usage: last.Usage}, nil
		}
		preparedCalls := prepareToolCalls(last.ToolCalls)
		validCalls := make([]model.ToolCall, 0, len(preparedCalls))
		for _, prepared := range preparedCalls {
			if prepared.err == nil {
				validCalls = append(validCalls, prepared.call)
			}
		}
		l.Context.Add(model.Message{Role: "assistant", Content: last.Content, ToolCalls: validCalls})
		l.emitContext(events)
		backgroundAgentIDs := make([]int, 0)
		for _, prepared := range preparedCalls {
			call := prepared.call
			if prepared.err != nil {
				message := invalidToolCallRecovery(call, prepared.err)
				if events.OnToolOutput != nil {
					events.OnToolOutput("recovery", message)
				}
				l.Context.Add(model.Message{Role: "system", Content: message})
				l.emitContext(events)
				continue
			}
			args := prepared.args
			t, ok := l.Tools.Get(call.Function.Name)
			if !ok {
				result := tool.Result{OK: false, Error: "tool not found: " + call.Function.Name}
				l.Context.Add(model.Message{Role: "tool", Name: call.Function.Name, ToolCallID: call.ID, Content: result.Error})
				l.emitContext(events)
				if events.OnToolEnd != nil {
					events.OnToolEnd(call.Function.Name, result)
				}
				continue
			}
			if allowed, desc := t.NeedsPermission(args); allowed && events.ConfirmPermission != nil && !events.ConfirmPermission(call.Function.Name, desc, args) {
				result := tool.Result{OK: false, Error: "permission denied"}
				l.Context.Add(model.Message{Role: "tool", Name: call.Function.Name, ToolCallID: call.ID, Content: result.Error})
				l.emitContext(events)
				if events.OnToolEnd != nil {
					events.OnToolEnd(call.Function.Name, result)
				}
				continue
			}
			if events.OnToolStart != nil {
				events.OnToolStart(call.Function.Name, args)
			}
			beforeCheckpoint := map[string]*string(nil)
			if l.Checkpoints != nil && l.Checkpoints.Enabled() {
				beforeCheckpoint = l.Checkpoints.Snapshot(call.Function.Name, args)
			}
			result := l.Tools.Run(ctx, call.Function.Name, args, func(line string) {
				if events.OnToolOutput != nil {
					events.OnToolOutput(call.Function.Name, line)
				}
			})
			if l.Checkpoints != nil && l.Checkpoints.Enabled() {
				checkpointResult := map[string]any{"ok": result.OK, "output": result.Output, "error": result.Error}
				if _, checkpointErr := l.Checkpoints.Save(call.Function.Name, args, checkpointResult, result.OK, beforeCheckpoint); checkpointErr != nil {
					warning := "checkpoint gagal disimpan: " + checkpointErr.Error()
					if events.OnToolOutput != nil {
						events.OnToolOutput("checkpoint", warning)
					}
					l.Context.Add(model.Message{Role: "system", Content: "⚠ " + warning})
				}
			}
			if events.OnToolEnd != nil {
				events.OnToolEnd(call.Function.Name, result)
			}
			content, _ := json.Marshal(result)
			l.Context.Add(model.Message{Role: "tool", Name: call.Function.Name, ToolCallID: call.ID, Content: string(content)})
			l.emitContext(events)
			if call.Function.Name == "spawn_agent" && isBackgroundSpawn(args) && result.OK {
				if id, ok := spawnedAgentID(result.Output); ok {
					backgroundAgentIDs = append(backgroundAgentIDs, id)
				}
			}
		}
		if len(backgroundAgentIDs) > 0 {
			if awaiting, ok := l.Tools.Get("await_agents"); ok {
				if monitor, ok := awaiting.(interface{ MonitorBackground([]int) }); ok {
					monitor.MonitorBackground(uniqueAgentIDs(backgroundAgentIDs))
				}
			}
		}
	}
	return last, fmt.Errorf("agent reached max iterations (%d)", limit)
}

func (l *Loop) emitContext(events Events) {
	if events.OnContextUpdated != nil && l.Context != nil {
		events.OnContextUpdated(l.Context.TokenEstimate(), l.Context.MaxTokens())
	}
}

type preparedToolCall struct {
	call model.ToolCall
	args map[string]any
	err  error
}

func prepareToolCalls(calls []model.ToolCall) []preparedToolCall {
	prepared := make([]preparedToolCall, 0, len(calls))
	for _, call := range calls {
		args, err := decodeToolCallArguments(call)
		prepared = append(prepared, preparedToolCall{call: call, args: args, err: err})
	}
	return prepared
}

func decodeToolCallArguments(call model.ToolCall) (map[string]any, error) {
	if strings.TrimSpace(call.ID) == "" {
		return nil, fmt.Errorf("ID tool call kosong")
	}
	if strings.TrimSpace(call.Function.Name) == "" {
		return nil, fmt.Errorf("nama tool kosong")
	}
	args := map[string]any{}
	arguments := strings.TrimSpace(call.Function.Arguments)
	if arguments == "" {
		return args, nil
	}
	if err := json.Unmarshal([]byte(arguments), &args); err != nil {
		return nil, fmt.Errorf("argumen harus berupa object JSON valid: %w", err)
	}
	if args == nil {
		return map[string]any{}, nil
	}
	return args, nil
}

func invalidToolCallRecovery(call model.ToolCall, err error) string {
	name := strings.TrimSpace(call.Function.Name)
	if name == "" {
		name = "tool"
	}
	return fmt.Sprintf("Tool call %s tidak dijalankan karena format argumennya rusak (%v). Buat ulang satu tool call %s dengan arguments berupa satu object JSON lengkap dan valid sesuai schema. Jangan kirim ulang fragmen atau JSON yang digabung.", name, err, name)
}

func hasToolResults(messages []model.Message) bool {
	for _, message := range messages {
		if message.Role == "tool" {
			return true
		}
	}
	return false
}

func shouldAutonomouslyContinue(content string) bool {
	lower := strings.ToLower(content)
	continueSignals := []string{"selanjutnya", "berikutnya", "mari kita", "akan saya", "sekarang saya"}
	stopSignals := []string{"selesai", "done", "berhasil", "complete", "sukses", "✅", "dibuat", "terdeploy"}
	for _, signal := range stopSignals {
		if strings.Contains(lower, signal) {
			return false
		}
	}
	for _, signal := range continueSignals {
		if strings.Contains(lower, signal) {
			return true
		}
	}
	return false
}

func isBackgroundSpawn(args map[string]any) bool {
	background, _ := args["background"].(bool)
	return background
}

func spawnedAgentID(output any) (int, bool) {
	var id int
	if count, _ := fmt.Sscanf(fmt.Sprint(output), "ghost #%d started", &id); count == 1 && id > 0 {
		return id, true
	}
	return 0, false
}

func uniqueAgentIDs(ids []int) []int {
	unique := make([]int, 0, len(ids))
	seen := map[int]struct{}{}
	for _, id := range ids {
		if id <= 0 {
			continue
		}
		if _, exists := seen[id]; exists {
			continue
		}
		seen[id] = struct{}{}
		unique = append(unique, id)
	}
	return unique
}

func mergeRequestMessages(messages, prelude []model.Message) []model.Message {
	if len(prelude) == 0 {
		return messages
	}
	merged := make([]model.Message, 0, len(messages)+len(prelude))
	if len(messages) > 0 && messages[0].Role == "system" {
		merged = append(merged, messages[0])
		merged = append(merged, prelude...)
		merged = append(merged, messages[1:]...)
		return merged
	}
	merged = append(merged, prelude...)
	return append(merged, messages...)
}

func definitions(registry *tool.Registry) []model.ToolDefinition {
	out := make([]model.ToolDefinition, 0)
	for _, definition := range registry.Definitions() {
		raw, _ := json.Marshal(definition.Parameters)
		out = append(out, model.ToolDefinition{Type: "function", Function: model.ToolFunction{Name: definition.Name, Description: definition.Description, Parameters: raw}})
	}
	return out
}
