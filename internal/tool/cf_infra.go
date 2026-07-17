package tool

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/autokeren/autokeren/internal/config"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type CFKV struct{ Config config.Config }
type CFD1 struct{ Config config.Config }

func (c CFKV) Definition() Definition {
	return Definition{Name: "cf_kv", Description: "Cloudflare KV operations.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string"}, "namespace_id": map[string]any{"type": "string"}, "key": map[string]any{"type": "string"}, "value": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (c CFKV) NeedsPermission(args map[string]any) (bool, string) {
	a, _ := args["action"].(string)
	return true, "Cloudflare KV " + a
}
func (c CFKV) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	acct := c.Config.Cloudflare.AccountID
	token := c.Config.Cloudflare.APIToken
	if acct == "" || token == "" {
		return Result{OK: false, Error: "Cloudflare account_id/api_token belum diisi"}
	}
	action, _ := args["action"].(string)
	ns, _ := args["namespace_id"].(string)
	key, _ := args["key"].(string)
	value, _ := args["value"].(string)
	base := "https://api.cloudflare.com/client/v4/accounts/" + url.PathEscape(acct)
	switch action {
	case "list_namespaces":
		return cfRequest(ctx, http.MethodGet, base+"/storage/kv/namespaces", token, nil)
	case "list_keys":
		return cfRequest(ctx, http.MethodGet, base+"/storage/kv/namespaces/"+url.PathEscape(ns)+"/keys", token, nil)
	case "get":
		return cfRequest(ctx, http.MethodGet, base+"/storage/kv/namespaces/"+url.PathEscape(ns)+"/values/"+url.PathEscape(key), token, nil)
	case "put":
		return cfRequest(ctx, http.MethodPut, base+"/storage/kv/namespaces/"+url.PathEscape(ns)+"/values/"+url.PathEscape(key), token, []byte(value))
	default:
		return Result{OK: false, Error: "action KV tidak dikenal"}
	}
}
func (c CFD1) Definition() Definition {
	return Definition{Name: "cf_d1", Description: "Cloudflare D1 query and database list.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"action": map[string]any{"type": "string"}, "database_id": map[string]any{"type": "string"}, "sql": map[string]any{"type": "string"}}, "required": []string{"action"}}}
}
func (c CFD1) NeedsPermission(args map[string]any) (bool, string) {
	a, _ := args["action"].(string)
	return true, "Cloudflare D1 " + a
}
func (c CFD1) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	acct := c.Config.Cloudflare.AccountID
	token := c.Config.Cloudflare.APIToken
	if acct == "" || token == "" {
		return Result{OK: false, Error: "Cloudflare account_id/api_token belum diisi"}
	}
	action, _ := args["action"].(string)
	base := "https://api.cloudflare.com/client/v4/accounts/" + url.PathEscape(acct)
	if action == "list" {
		return cfRequest(ctx, http.MethodGet, base+"/d1/database", token, nil)
	}
	db, _ := args["database_id"].(string)
	sql, _ := args["sql"].(string)
	if db == "" || sql == "" {
		return Result{OK: false, Error: "database_id dan sql wajib"}
	}
	payload, _ := json.Marshal(map[string]string{"sql": sql})
	return cfRequest(ctx, http.MethodPost, base+"/d1/database/"+url.PathEscape(db)+"/query", token, payload)
}
func cfRequest(ctx context.Context, method, endpoint, token string, body []byte) Result {
	req, err := http.NewRequestWithContext(ctx, method, endpoint, bytes.NewReader(body))
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	req.Header.Set("Authorization", "Bearer "+token)
	if method == http.MethodPut {
		req.Header.Set("Content-Type", "text/plain")
	} else {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := (&http.Client{Timeout: 30 * time.Second}).Do(req)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(resp.Body, 2<<20))
	var out any
	if json.Unmarshal(data, &out) != nil {
		out = string(data)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return Result{OK: false, Output: out, Error: fmt.Sprintf("Cloudflare HTTP %d", resp.StatusCode)}
	}
	return Result{OK: true, Output: out}
}

var _ = strings.TrimSpace
