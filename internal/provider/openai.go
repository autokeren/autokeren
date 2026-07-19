package provider

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/autokeren/autokeren/internal/model"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

type OpenAICompatible struct {
	Endpoint string
	APIKey   string
	Client   *http.Client
}

func (p OpenAICompatible) Complete(ctx context.Context, request model.Request, onChunk ChunkHandler) (model.Response, error) {
	if p.Endpoint == "" {
		return model.Response{}, fmt.Errorf("provider endpoint is empty")
	}
	if p.Client == nil {
		p.Client = http.DefaultClient
	}
	request.Stream = true
	body, err := json.Marshal(request)
	if err != nil {
		return model.Response{}, fmt.Errorf("marshal provider request: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, p.Endpoint, bytes.NewReader(body))
	if err != nil {
		return model.Response{}, fmt.Errorf("create provider request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if p.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+p.APIKey)
	}
	resp, err := p.Client.Do(req)
	if err != nil {
		return model.Response{}, &Error{Cause: fmt.Errorf("provider request: %w", err)}
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		data, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return model.Response{}, &Error{
			Status:     resp.StatusCode,
			RetryAfter: retryAfter(resp.Header.Get("Retry-After")),
			Cause:      fmt.Errorf("provider status %d: %s", resp.StatusCode, strings.TrimSpace(string(data))),
		}
	}
	result, streamStarted, err := parseSSE(resp.Body, onChunk)
	if err != nil {
		return model.Response{}, &Error{StreamStarted: streamStarted, Cause: err}
	}
	result.Usage.NeuronsUsed = headerInt(resp.Header.Get("X-Neurons-Used"))
	result.Usage.NeuronsRemaining = headerInt(resp.Header.Get("X-Neurons-Remaining"))
	result.Usage.NeuronsQuota = headerInt(resp.Header.Get("X-Neurons-Quota"))
	return result, nil
}

func retryAfter(value string) time.Duration {
	value = strings.TrimSpace(value)
	if value == "" {
		return 0
	}
	if seconds, err := strconv.Atoi(value); err == nil && seconds > 0 {
		return time.Duration(seconds) * time.Second
	}
	if when, err := http.ParseTime(value); err == nil {
		if delay := time.Until(when); delay > 0 {
			return delay
		}
	}
	return 0
}

func headerInt(value string) int {
	parsed, err := strconv.Atoi(value)
	if err != nil || parsed < 0 {
		return 0
	}
	return parsed
}

type streamEvent struct {
	Model   string `json:"model"`
	Choices []struct {
		Delta struct {
			Content   string `json:"content"`
			ToolCalls []struct {
				Index    int    `json:"index"`
				ID       string `json:"id"`
				Type     string `json:"type"`
				Function struct {
					Name      string `json:"name"`
					Arguments string `json:"arguments"`
				} `json:"function"`
			} `json:"tool_calls"`
		} `json:"delta"`
		FinishReason *string `json:"finish_reason"`
	} `json:"choices"`
	Usage model.Usage `json:"usage"`
}

func parseSSE(reader io.Reader, onChunk ChunkHandler) (model.Response, bool, error) {
	var result model.Response
	var calls []model.ToolCall
	streamStarted := false
	scanner := bufio.NewScanner(reader)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if !strings.HasPrefix(line, "data:") {
			continue
		}
		payload := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
		if payload == "[DONE]" {
			break
		}
		streamStarted = true
		var event streamEvent
		if err := json.Unmarshal([]byte(payload), &event); err != nil {
			return model.Response{}, streamStarted, fmt.Errorf("decode provider event: %w", err)
		}
		result.Model = event.Model
		result.Usage = event.Usage
		for _, choice := range event.Choices {
			if choice.FinishReason != nil {
				result.FinishReason = *choice.FinishReason
			}
			if choice.Delta.Content != "" {
				result.Content += choice.Delta.Content
				if onChunk != nil {
					if err := onChunk(choice.Delta.Content); err != nil {
						return model.Response{}, streamStarted, err
					}
				}
			}
			for _, call := range choice.Delta.ToolCalls {
				for len(calls) <= call.Index {
					calls = append(calls, model.ToolCall{Type: "function"})
				}
				if call.ID != "" {
					calls[call.Index].ID = call.ID
				}
				if call.Type != "" {
					calls[call.Index].Type = call.Type
				}
				calls[call.Index].Function.Name = mergeToolName(calls[call.Index].Function.Name, call.Function.Name)
				calls[call.Index].Function.Arguments = mergeToolArguments(calls[call.Index].Function.Arguments, call.Function.Arguments)
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return model.Response{}, streamStarted, fmt.Errorf("read provider stream: %w", err)
	}
	result.ToolCalls = calls
	return result, streamStarted, nil
}

func mergeToolName(current, fragment string) string {
	return mergeStreamFragment(current, fragment)
}

func mergeToolArguments(current, fragment string) string {
	return mergeStreamFragment(current, fragment)
}

func mergeStreamFragment(current, fragment string) string {
	if fragment == "" || current == fragment {
		return current
	}
	if current == "" || strings.HasPrefix(fragment, current) {
		return fragment
	}
	if strings.HasSuffix(current, fragment) {
		return current
	}
	limit := len(current)
	if len(fragment) < limit {
		limit = len(fragment)
	}
	for size := limit; size > 0; size-- {
		if strings.HasSuffix(current, fragment[:size]) {
			return current + fragment[size:]
		}
	}
	return current + fragment
}
