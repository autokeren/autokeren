package tool

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type FetchURL struct{ Client *http.Client }

func (f FetchURL) Definition() Definition {
	return Definition{Name: "fetch_url", Description: "Fetch readable text from a public URL.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"url": map[string]any{"type": "string"}, "max_chars": map[string]any{"type": "integer"}}, "required": []string{"url"}}}
}
func (f FetchURL) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (f FetchURL) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	raw, _ := args["url"].(string)
	u, err := url.Parse(raw)
	if err != nil || u.Scheme != "https" && u.Scheme != "http" {
		return Result{OK: false, Error: "URL tidak valid"}
	}
	max := 5000
	if v, ok := args["max_chars"].(float64); ok && v > 0 {
		max = int(v)
	}
	client := f.Client
	if client == nil {
		client = &http.Client{Timeout: 30 * time.Second}
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, raw, nil)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	req.Header.Set("User-Agent", "autokeren-go/1.0")
	resp, err := client.Do(req)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return Result{OK: false, Error: fmt.Sprintf("HTTP %d", resp.StatusCode)}
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, int64(max*4)))
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	text := strings.TrimSpace(string(data))
	if len(text) > max {
		text = text[:max]
	}
	return Result{OK: true, Output: text}
}
