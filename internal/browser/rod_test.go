package browser

import (
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
