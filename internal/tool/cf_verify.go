package tool

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/autokeren/autokeren/internal/browser"
)

type CFVerify struct {
	Root    string
	Browser *browser.BrowserManager
}

func (v CFVerify) Definition() Definition {
	return Definition{Name: "cf_verify", Description: "Verify deployed URL with HTTP and native Rod checks.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"url": map[string]any{"type": "string"}, "assert_text": map[string]any{"type": "string"}, "assert_selector": map[string]any{"type": "string"}, "wait_seconds": map[string]any{"type": "number"}}, "required": []string{"url"}}}
}
func (v CFVerify) NeedsPermission(map[string]any) (bool, string) { return false, "" }
func (v CFVerify) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	url, _ := args["url"].(string)
	if url == "" {
		return Result{OK: false, Error: "url wajib"}
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	resp, err := (&http.Client{Timeout: 15 * time.Second}).Do(req)
	if err != nil {
		return Result{OK: false, Error: fmt.Sprintf("HTTP check gagal: %v", err)}
	}
	_ = resp.Body.Close()
	errors := []string{}
	if resp.StatusCode >= 400 {
		errors = append(errors, fmt.Sprintf("HTTP %d", resp.StatusCode))
	}
	assertions := []string{}
	report := map[string]any{"url": url, "http_status": resp.StatusCode, "timestamp": time.Now().UTC().Format(time.RFC3339)}
	if v.Browser != nil {
		if _, navErr := v.Browser.Execute("navigate", map[string]interface{}{"url": url}); navErr != nil {
			errors = append(errors, "browser: "+navErr.Error())
		} else {
			if wait, ok := args["wait_seconds"].(float64); ok && wait > 0 && wait < 30 {
				time.Sleep(time.Duration(wait * float64(time.Second)))
			}
			for _, assertion := range []struct{ value, kind string }{{getString(args, "assert_text"), "visible_text"}, {getString(args, "assert_selector"), "selector"}} {
				if assertion.value == "" {
					continue
				}
				out, assertErr := v.Browser.Execute("assert", map[string]interface{}{"assertion": map[string]interface{}{"kind": assertion.kind, "value": assertion.value}})
				if assertErr != nil {
					errors = append(errors, assertErr.Error())
				} else {
					message := fmt.Sprint(out)
					assertions = append(assertions, message)
					if passed, ok := out.(map[string]interface{})["ok"].(bool); !ok || !passed {
						errors = append(errors, "assertion gagal: "+message)
					}
				}
			}
			if screenshot, screenshotErr := v.Browser.Execute("screenshot", nil); screenshotErr == nil {
				if data, ok := screenshot.(map[string]interface{}); ok {
					if encoded, ok := data["base64"].(string); ok {
						dir := filepath.Join(v.Root, ".ak-verification")
						if os.MkdirAll(dir, 0o700) == nil {
							if bytes, decodeErr := base64.StdEncoding.DecodeString(encoded); decodeErr == nil && os.WriteFile(filepath.Join(dir, "latest.png"), bytes, 0o600) == nil {
								report["screenshot_path"] = filepath.Join(dir, "latest.png")
							}
						}
					}
				}
			}
		}
	}
	report["assertions"], report["errors"], report["ok"] = assertions, errors, len(errors) == 0
	dir := filepath.Join(v.Root, ".ak-verification")
	if os.MkdirAll(dir, 0o700) == nil {
		if data, marshalErr := json.MarshalIndent(report, "", "  "); marshalErr == nil {
			_ = os.WriteFile(filepath.Join(dir, "latest.json"), data, 0o600)
		}
	}
	data, _ := json.MarshalIndent(report, "", "  ")
	if len(errors) > 0 {
		return Result{OK: false, Output: string(data), Error: "verifikasi deployment menemukan masalah"}
	}
	return Result{OK: true, Output: string(data)}
}
func getString(args map[string]any, key string) string { value, _ := args[key].(string); return value }
