package browser

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

func TestAssertionExpressionWrapsValuesAsJavaScriptFunctions(t *testing.T) {
	expression, err := assertionExpression("visible_text", `Keren "Shoes"`)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(expression, "() =>") || !strings.Contains(expression, `includes("Keren \"Shoes\"")`) {
		t.Fatalf("unexpected visible text expression: %s", expression)
	}
	selector, err := assertionExpression("selector", `[data-name="shoe"]`)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(selector, "() =>") || !strings.Contains(selector, `querySelector("[data-name=\"shoe\"]")`) {
		t.Fatalf("unexpected selector expression: %s", selector)
	}
	if _, err := assertionExpression("unknown", "value"); err == nil {
		t.Fatal("expected unsupported assertion kind to fail")
	}
}

func TestBrowserUnavailableReturnsActionableErrorWithoutPanic(t *testing.T) {
	originalLaunch := launchBrowser
	launchBrowser = func() (string, error) { return "", errors.New("browser binary missing") }
	t.Cleanup(func() { launchBrowser = originalLaunch })

	_, err := (&BrowserManager{}).Execute("navigate", map[string]interface{}{"url": "https://example.com"})
	if err == nil || !strings.Contains(err.Error(), "browser automation tidak tersedia") {
		t.Fatalf("expected actionable browser error, got %v", err)
	}
}

func TestBrowserCloseDoesNotLaunchBrowser(t *testing.T) {
	originalLaunch := launchBrowser
	called := false
	launchBrowser = func() (string, error) {
		called = true
		return "", errors.New("should not launch")
	}
	t.Cleanup(func() { launchBrowser = originalLaunch })

	result, err := (&BrowserManager{}).Execute("close", nil)
	if err != nil || called || result.(map[string]interface{})["status"] != "closed" {
		t.Fatalf("result=%#v err=%v launchCalled=%t", result, err, called)
	}
}

func TestWindowsBrowserUnavailableErrorMentionsOverride(t *testing.T) {
	err := browserUnavailableError("windows", errors.New("not found"))
	if !strings.Contains(err.Error(), "AUTOKEREN_BROWSER_PATH") || !strings.Contains(err.Error(), "Chrome atau Edge") {
		t.Fatalf("unexpected Windows guidance: %v", err)
	}
}

func TestBrowserAutomationSmoke(t *testing.T) {
	if os.Getenv("AUTOKEREN_BROWSER_SMOKE") != "1" {
		t.Skip("set AUTOKEREN_BROWSER_SMOKE=1 to run a real browser automation smoke test")
	}
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		_, _ = writer.Write([]byte(`<!doctype html><html><head><title>KerenKicks</title></head><body><h1>KerenKicks</h1><button id="buy" onclick="this.textContent='Added'">Buy</button></body></html>`))
	}))
	defer server.Close()
	manager := &BrowserManager{}
	defer manager.Close()
	if _, err := manager.Execute("navigate", map[string]interface{}{"url": server.URL}); err != nil {
		t.Fatal(err)
	}
	snapshot, err := manager.Execute("snapshot", map[string]interface{}{})
	if err != nil || !strings.Contains(strings.ToLower(snapshot.(map[string]interface{})["dom_tree"].(string)), "buy") {
		t.Fatalf("snapshot=%#v err=%v", snapshot, err)
	}
	if _, err := manager.Execute("click", map[string]interface{}{"selector": "#buy"}); err != nil {
		t.Fatal(err)
	}
	assertion, err := manager.Execute("assert", map[string]interface{}{"assertion": map[string]interface{}{"kind": "visible_text", "value": "Added"}})
	if err != nil || !assertion.(map[string]interface{})["ok"].(bool) {
		t.Fatalf("assertion=%#v err=%v", assertion, err)
	}
	screenshot, err := manager.Execute("screenshot", map[string]interface{}{})
	if err != nil || screenshot.(map[string]interface{})["bytes"].(int) == 0 {
		t.Fatalf("screenshot=%#v err=%v", screenshot, err)
	}
}
