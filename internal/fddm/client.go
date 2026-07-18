package fddm

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"
)

const defaultTimeout = 10 * time.Second

var (
	sensitiveAssignment = regexp.MustCompile(`(?i)(["']?(?:api[_-]?key|password|secret|token|authorization)["']?\s*[:=]\s*["']?)([^\s,"'}\]]+)`)
	bearerToken         = regexp.MustCompile(`(?i)\bbearer\s+[a-z0-9._~+/=-]+`)
	bareToken           = regexp.MustCompile(`(?i)\b(?:sk|ak|cf|aiza)[_-][a-z0-9._-]{8,}\b`)
)

type Config struct {
	URL     string
	APIKey  string
	Timeout time.Duration
}

type Client struct {
	baseURL string
	apiKey  string
	timeout time.Duration
	http    *http.Client
}

type Hit struct {
	ScentID    string  `json:"scent_id"`
	Type       string  `json:"type"`
	Score      float64 `json:"score"`
	Similarity float64 `json:"similarity"`
	Artifact   string  `json:"artifact"`
}

func New(cfg Config, httpClient *http.Client) *Client {
	timeout := cfg.Timeout
	if timeout <= 0 {
		timeout = defaultTimeout
	}
	if httpClient == nil {
		httpClient = &http.Client{}
	}
	return &Client{
		baseURL: strings.TrimRight(strings.TrimSpace(cfg.URL), "/"),
		apiKey:  strings.TrimSpace(cfg.APIKey),
		timeout: timeout,
		http:    httpClient,
	}
}

func (c *Client) Enabled() bool {
	return c != nil && c.baseURL != ""
}

func (c *Client) Sniff(ctx context.Context, text string, topK int, radius float64) ([]Hit, error) {
	if !c.Enabled() {
		return nil, errors.New("FDDM belum dikonfigurasi")
	}
	if topK <= 0 {
		topK = 3
	}
	if topK > 10 {
		topK = 10
	}
	if radius <= 0 || radius > 1 {
		radius = 0.2
	}
	var hits []Hit
	err := c.request(ctx, http.MethodPost, "/api/sniff_text", map[string]any{
		"text":   sanitize(text, 2000),
		"top_k":  topK,
		"radius": radius,
	}, &hits)
	if err != nil {
		return nil, err
	}
	for index := range hits {
		hits[index].Type = sanitize(hits[index].Type, 80)
		hits[index].Artifact = sanitize(hits[index].Artifact, 200)
	}
	return hits, nil
}

func (c *Client) SniffContext(ctx context.Context, query string) (string, error) {
	hits, err := c.Sniff(ctx, query, 3, 0.2)
	if err != nil || len(hits) == 0 {
		return "", err
	}
	var builder strings.Builder
	builder.WriteString("🐜 FDDM AUTO-SNIFF: Memori relevan dari sesi/project sebelumnya:")
	for index, hit := range hits {
		builder.WriteString(fmt.Sprintf("\n  %d. [%s] (score %.2f) %s", index+1, hit.Type, hit.Score, hit.Artifact))
	}
	return limitRunes(builder.String(), 1200), nil
}

func (c *Client) EmitCompletion(ctx context.Context, task, response string) error {
	if !c.Enabled() || len(strings.TrimSpace(response)) < 20 {
		return nil
	}
	text := "Task: " + sanitize(task, 200) + "\nResult: " + sanitize(response, 500)
	return c.Emit(ctx, "decision", text, "autokeren_auto", 0.6)
}

func (c *Client) Emit(ctx context.Context, scentType, text, emitterID string, baseScore float64) error {
	if !c.Enabled() {
		return errors.New("FDDM belum dikonfigurasi")
	}
	if strings.TrimSpace(scentType) == "" {
		scentType = "observation"
	}
	if strings.TrimSpace(emitterID) == "" {
		emitterID = "autokeren_agent"
	}
	if baseScore <= 0 || baseScore > 1 {
		baseScore = 0.7
	}
	var response map[string]any
	return c.request(ctx, http.MethodPost, "/api/emit_text", map[string]any{
		"type":       sanitize(scentType, 80),
		"text":       sanitize(text, 4000),
		"emitter_id": sanitize(emitterID, 160),
		"base_score": baseScore,
	}, &response)
}

func (c *Client) Execute(ctx context.Context, action string, args map[string]any) (any, error) {
	switch action {
	case "emit":
		return c.executeEmit(ctx, args)
	case "sniff":
		hits, err := c.Sniff(ctx, stringArg(args, "text"), intArg(args, "top_k"), floatArg(args, "radius"))
		return hits, err
	case "stats":
		var output map[string]any
		err := c.request(ctx, http.MethodGet, "/api/stats", nil, &output)
		return output, err
	case "decay":
		var output map[string]any
		err := c.request(ctx, http.MethodPost, "/api/decay", map[string]any{}, &output)
		return output, err
	case "trust":
		var output map[string]any
		err := c.request(ctx, http.MethodPost, "/api/trust", map[string]any{
			"emitter_id": sanitize(stringArg(args, "emitter_id"), 160),
			"success":    boolArg(args, "success", true),
		}, &output)
		return output, err
	default:
		return nil, errors.New("aksi FDDM tidak dikenal")
	}
}

func (c *Client) executeEmit(ctx context.Context, args map[string]any) (any, error) {
	if !c.Enabled() {
		return nil, errors.New("FDDM belum dikonfigurasi")
	}
	scentType := stringArg(args, "type")
	if scentType == "" {
		scentType = "observation"
	}
	emitterID := stringArg(args, "emitter_id")
	if emitterID == "" {
		emitterID = "autokeren_agent"
	}
	var output map[string]any
	err := c.request(ctx, http.MethodPost, "/api/emit_text", map[string]any{
		"type":       sanitize(scentType, 80),
		"text":       sanitize(stringArg(args, "text"), 4000),
		"emitter_id": sanitize(emitterID, 160),
		"base_score": 0.7,
	}, &output)
	return output, err
}

func (c *Client) request(ctx context.Context, method, path string, payload any, output any) error {
	if !c.Enabled() {
		return errors.New("FDDM belum dikonfigurasi")
	}
	requestContext, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()
	var body io.Reader
	if payload != nil {
		data, err := json.Marshal(payload)
		if err != nil {
			return fmt.Errorf("serialisasi request FDDM: %w", err)
		}
		body = bytes.NewReader(data)
	}
	request, err := http.NewRequestWithContext(requestContext, method, c.baseURL+path, body)
	if err != nil {
		return fmt.Errorf("buat request FDDM: %w", err)
	}
	if payload != nil {
		request.Header.Set("Content-Type", "application/json")
	}
	if c.apiKey != "" {
		request.Header.Set("Authorization", "Bearer "+c.apiKey)
	}
	response, err := c.http.Do(request)
	if err != nil {
		return fmt.Errorf("request FDDM: %w", err)
	}
	defer response.Body.Close()
	if response.StatusCode >= http.StatusBadRequest {
		_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 4096))
		return fmt.Errorf("FDDM HTTP %d", response.StatusCode)
	}
	if err := json.NewDecoder(io.LimitReader(response.Body, 1<<20)).Decode(output); err != nil {
		return fmt.Errorf("decode response FDDM: %w", err)
	}
	return nil
}

func sanitize(value string, maximum int) string {
	value = sensitiveAssignment.ReplaceAllString(value, "$1[REDACTED]")
	value = bearerToken.ReplaceAllStringFunc(value, func(string) string { return "Bearer [REDACTED]" })
	value = bareToken.ReplaceAllString(value, "[REDACTED]")
	return limitRunes(value, maximum)
}

func limitRunes(value string, maximum int) string {
	if maximum <= 0 || utf8.RuneCountInString(value) <= maximum {
		return value
	}
	runes := []rune(value)
	return string(runes[:maximum])
}

func stringArg(args map[string]any, name string) string {
	value, _ := args[name].(string)
	return value
}

func intArg(args map[string]any, name string) int {
	switch value := args[name].(type) {
	case int:
		return value
	case int64:
		return int(value)
	case float64:
		return int(value)
	default:
		return 0
	}
}

func floatArg(args map[string]any, name string) float64 {
	switch value := args[name].(type) {
	case float64:
		return value
	case float32:
		return float64(value)
	case int:
		return float64(value)
	default:
		return 0
	}
}

func boolArg(args map[string]any, name string, fallback bool) bool {
	value, ok := args[name].(bool)
	if !ok {
		return fallback
	}
	return value
}
