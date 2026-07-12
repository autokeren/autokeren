package ipc

import (
	"context"
	"encoding/base64"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/input"
	"github.com/go-rod/rod/lib/launcher"
	"github.com/go-rod/rod/lib/proto"
)

type BrowserManager struct {
	browser *rod.Browser
	page    *rod.Page
	lock    sync.Mutex
}

var (
	globalBM     *BrowserManager
	globalBMLock sync.Mutex
)

func GetBrowserManager() *BrowserManager {
	globalBMLock.Lock()
	defer globalBMLock.Unlock()
	if globalBM == nil {
		globalBM = &BrowserManager{}
	}
	return globalBM
}

func (bm *BrowserManager) Close() {
	bm.lock.Lock()
	defer bm.lock.Unlock()
	if bm.browser != nil {
		bm.browser.MustClose()
		bm.browser = nil
		bm.page = nil
	}
}

func (bm *BrowserManager) getPage() (*rod.Page, error) {
	if bm.browser == nil {
		u := launcher.New().NoSandbox(true).MustLaunch()
		browser := rod.New().ControlURL(u).MustConnect()
		bm.browser = browser
	}
	if bm.page == nil {
		// Create a new target page using default proto options
		page, err := bm.browser.Page(proto.TargetCreateTarget{})
		if err != nil {
			return nil, err
		}
		bm.page = page
	}
	return bm.page, nil
}

func (bm *BrowserManager) Execute(action string, args map[string]interface{}) (interface{}, error) {
	bm.lock.Lock()
	defer bm.lock.Unlock()

	page, err := bm.getPage()
	if err != nil {
		return nil, fmt.Errorf("failed to get browser page: %v", err)
	}

	// Gunakan timeout 15 detik untuk semua interaksi agar tidak terjadi hanging permanen
	page = page.Timeout(15 * time.Second)

	switch action {
	case "navigate":
		url, _ := args["url"].(string)
		if url == "" {
			return nil, errors.New("url parameter is required")
		}
		err := page.Navigate(url)
		if err != nil {
			return nil, err
		}
		// Wait for page load
		page.MustWaitLoad()
		time.Sleep(2 * time.Second) // Jedah halus agar JS render
		return map[string]interface{}{"status": "navigated", "url": url}, nil

	case "snapshot":
		// Evaluasi JS untuk mengekstrak struktur DOM visual
		// Kita berikan ref id unik pada elemen interaktif
		jsSnippet := `() => {
			const elements = document.querySelectorAll('a, button, input, select, textarea, [role="button"], [contenteditable="true"]');
			let output = [];
			elements.forEach((el, index) => {
				const ref = index + 1;
				el.setAttribute('data-ak-ref', ref);
				
				let text = el.innerText || el.placeholder || el.value || '';
				text = text.trim().substring(0, 100);
				
				let label = el.tagName.toLowerCase();
				if (el.tagName === 'INPUT') {
					label += ":" + (el.type || 'text');
				}
				
				output.push("[" + ref + "] " + label.toUpperCase() + ": " + (text || '[kosong]'));
			});
			return output.join('\n');
		}`
		res, err := page.Eval(jsSnippet)
		if err != nil {
			return nil, err
		}
		valStr := ""
		if res != nil {
			valStr = res.Value.String()
		}
		return map[string]interface{}{"dom_tree": valStr}, nil

	case "click":
		var el *rod.Element
		if refVal, ok := args["ref"].(float64); ok {
			ref := int(refVal)
			el, err = page.Element(fmt.Sprintf("[data-ak-ref='%d']", ref))
		} else if selector, ok := args["selector"].(string); ok {
			el, err = page.Element(selector)
		} else {
			return nil, errors.New("ref or selector parameter is required")
		}
		if err != nil {
			return nil, fmt.Errorf("element not found: %v", err)
		}
		err = el.Click(proto.InputMouseButtonLeft, 1)
		if err != nil {
			return nil, err
		}
		time.Sleep(1 * time.Second)
		return map[string]interface{}{"status": "clicked"}, nil

	case "type":
		var el *rod.Element
		if refVal, ok := args["ref"].(float64); ok {
			ref := int(refVal)
			el, err = page.Element(fmt.Sprintf("[data-ak-ref='%d']", ref))
		} else if selector, ok := args["selector"].(string); ok {
			el, err = page.Element(selector)
		} else {
			return nil, errors.New("ref or selector parameter is required")
		}
		if err != nil {
			return nil, fmt.Errorf("element not found: %v", err)
		}

		text, _ := args["text"].(string)
		err = el.Input(text)
		if err != nil {
			return nil, err
		}

		if pressEnter, _ := args["press_enter"].(bool); pressEnter {
			actions, err := el.KeyActions()
			if err != nil {
				return nil, err
			}
			err = actions.Press(input.Enter).Do()
			if err != nil {
				return nil, err
			}
			time.Sleep(1 * time.Second)
		}
		return map[string]interface{}{"status": "typed"}, nil

	case "eval":
		expression, _ := args["expression"].(string)
		if expression == "" {
			return nil, errors.New("expression parameter is required")
		}

		// Bungkus ekspresi JS dalam arrow function agar executor Go-Rod tidak melempar error
		// "TypeError: ...apply is not a function" saat mengevaluasi nilai non-fungsi.
		wrappedExpr := expression
		trimmed := strings.TrimSpace(expression)
		if !strings.HasPrefix(trimmed, "function") && !strings.HasPrefix(trimmed, "()") && !strings.Contains(trimmed, "=>") {
			if (strings.HasPrefix(trimmed, "(") && strings.HasSuffix(trimmed, ")")) || (!strings.Contains(trimmed, "return") && !strings.Contains(trimmed, ";")) {
				wrappedExpr = fmt.Sprintf("() => (%s)", expression)
			} else if strings.Contains(trimmed, "return") {
				wrappedExpr = fmt.Sprintf("() => { %s }", expression)
			} else {
				wrappedExpr = fmt.Sprintf("() => { return (%s); }", expression)
			}
		}

		res, err := page.Eval(wrappedExpr)
		if err != nil {
			return nil, err
		}
		valStr := ""
		if res != nil {
			valStr = res.Value.String()
		}
		return map[string]interface{}{"result": valStr}, nil

	case "screenshot":
		// Tangkap screenshot ke format PNG binary
		imgBytes, err := page.Screenshot(true, &proto.PageCaptureScreenshot{})
		if err != nil {
			return nil, err
		}

		base64Str := base64.StdEncoding.EncodeToString(imgBytes)
		return map[string]interface{}{
			"bytes":  len(imgBytes),
			"base64": base64Str,
		}, nil

	case "assert":
		assertion, _ := args["assertion"].(map[string]interface{})
		kind, _ := assertion["kind"].(string)
		value, _ := assertion["value"].(string)

		if kind == "visible_text" {
			expr := fmt.Sprintf("document.body.innerText.includes('%s')", value)
			res, err := page.Eval(expr)
			if err != nil {
				return nil, err
			}
			ok := false
			if res != nil {
				ok = res.Value.Bool()
			}
			return map[string]interface{}{"ok": ok, "message": fmt.Sprintf("assert visible_text '%s': %t", value, ok)}, nil
		} else if kind == "selector" {
			expr := fmt.Sprintf("!!document.querySelector('%s')", value)
			res, err := page.Eval(expr)
			if err != nil {
				return nil, err
			}
			ok := false
			if res != nil {
				ok = res.Value.Bool()
			}
			return map[string]interface{}{"ok": ok, "message": fmt.Sprintf("assert selector '%s': %t", value, ok)}, nil
		}
		return nil, fmt.Errorf("unknown assertion kind: %s", kind)

	default:
		return nil, fmt.Errorf("unknown action: %s", action)
	}
}

// Ensure context package is used to satisfy import checks
var _ context.Context
