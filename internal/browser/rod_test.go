package browser

import (
	"errors"
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
