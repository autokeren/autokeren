package engine

import (
	"context"
	"encoding/json"
	"fmt"
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
}

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
	limit := l.MaxIterations
	if limit <= 0 {
		limit = 50
	}
	var last model.Response
	recoveredFromLimit := false
	for iteration := 0; iteration < limit; iteration++ {
		request := model.Request{Model: l.Model, Messages: mergeRequestMessages(l.Context.Messages(), l.RequestPrelude), Tools: definitions(l.Tools), Temperature: l.Temperature, MaxTokens: l.MaxTokens}
		var onChunk provider.ChunkHandler
		if events.OnChunk != nil {
			onChunk = func(chunk string) error { events.OnChunk(chunk); return nil }
		}
		last, err := l.Runner.RunTurn(ctx, request, onChunk)
		if err != nil {
			if provider.IsContextLimit(err) && !recoveredFromLimit {
				before, after, changed := l.Context.Compact()
				if changed {
					recoveredFromLimit = true
					if events.OnRetry != nil {
						events.OnRetry(0, 0, fmt.Sprintf("context penuh; compact otomatis %d → %d token lalu mencoba ulang", before, after))
					}
					continue
				}
			}
			return model.Response{}, err
		}
		if len(last.ToolCalls) == 0 {
			l.Context.Add(model.Message{Role: "assistant", Content: last.Content})
			if strings.TrimSpace(last.Content) == "" {
				// Providers can occasionally emit an empty terminal SSE turn. Give
				// the model another turn instead of silently ending the session.
				continue
			}
			return last, nil
		}
		// Preserve any streamed reasoning/content alongside tool calls, but always
		// dispatch the calls before deciding that the turn is complete.
		l.Context.Add(model.Message{Role: "assistant", Content: last.Content, ToolCalls: last.ToolCalls})
		for _, call := range last.ToolCalls {
			args := map[string]any{}
			if call.Function.Arguments != "" {
				if err := json.Unmarshal([]byte(call.Function.Arguments), &args); err != nil {
					return model.Response{}, fmt.Errorf("invalid arguments for %s: %w", call.Function.Name, err)
				}
			}
			t, ok := l.Tools.Get(call.Function.Name)
			if !ok {
				result := tool.Result{OK: false, Error: "tool not found: " + call.Function.Name}
				l.Context.Add(model.Message{Role: "tool", Name: call.Function.Name, ToolCallID: call.ID, Content: result.Error})
				if events.OnToolEnd != nil {
					events.OnToolEnd(call.Function.Name, result)
				}
				continue
			}
			if allowed, desc := t.NeedsPermission(args); allowed && events.ConfirmPermission != nil && !events.ConfirmPermission(call.Function.Name, desc, args) {
				result := tool.Result{OK: false, Error: "permission denied"}
				l.Context.Add(model.Message{Role: "tool", Name: call.Function.Name, ToolCallID: call.ID, Content: result.Error})
				if events.OnToolEnd != nil {
					events.OnToolEnd(call.Function.Name, result)
				}
				continue
			}
			if events.OnToolStart != nil {
				events.OnToolStart(call.Function.Name, args)
			}
			result := l.Tools.Run(ctx, call.Function.Name, args, func(line string) {
				if events.OnToolOutput != nil {
					events.OnToolOutput(call.Function.Name, line)
				}
			})
			if events.OnToolEnd != nil {
				events.OnToolEnd(call.Function.Name, result)
			}
			content, _ := json.Marshal(result)
			l.Context.Add(model.Message{Role: "tool", Name: call.Function.Name, ToolCallID: call.ID, Content: string(content)})
		}
	}
	return last, fmt.Errorf("agent reached max iterations (%d)", limit)
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
