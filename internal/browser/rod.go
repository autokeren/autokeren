package browser

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"runtime"
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
	globalBM       *BrowserManager
	globalBMLock   sync.Mutex
	launchBrowser  = launchNativeBrowser
	connectBrowser = connectNativeBrowser
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
	bm.closeLocked()
}

func (bm *BrowserManager) closeLocked() {
	if bm.page != nil {
		_ = bm.page.Close()
		bm.page = nil
	}
	if bm.browser != nil {
		_ = bm.browser.Close()
		bm.browser = nil
	}
}

func (bm *BrowserManager) getPage() (*rod.Page, error) {
	if bm.browser == nil {
		u, err := launchBrowser()
		if err != nil {
			return nil, browserUnavailableError(runtime.GOOS, err)
		}
		browser, err := connectBrowser(u)
		if err != nil {
			return nil, browserUnavailableError(runtime.GOOS, err)
		}
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
	if action == "close" {
		bm.closeLocked()
		return map[string]interface{}{"status": "closed"}, nil
	}

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
		if err := page.WaitLoad(); err != nil {
			return nil, fmt.Errorf("wait page load: %w", err)
		}
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
		expr, err := assertionExpression(kind, value)
		if err != nil {
			return nil, err
		}
		res, err := page.Eval(expr)
		if err != nil {
			return nil, err
		}
		ok := false
		if res != nil {
			ok = res.Value.Bool()
		}
		return map[string]interface{}{"ok": ok, "message": fmt.Sprintf("assert %s '%s': %t", kind, value, ok)}, nil

	default:
		return nil, fmt.Errorf("unknown action: %s", action)
	}
}

func launchNativeBrowser() (string, error) {
	launcherConfig := launcher.New()
	if runtime.GOOS == "linux" {
		launcherConfig.NoSandbox(true)
	}
	if browserPath := strings.TrimSpace(os.Getenv("AUTOKEREN_BROWSER_PATH")); browserPath != "" {
		info, err := os.Stat(browserPath)
		if err != nil {
			return "", fmt.Errorf("browser path tidak dapat diakses: %w", err)
		}
		if info.IsDir() {
			return "", errors.New("AUTOKEREN_BROWSER_PATH harus menunjuk ke file executable browser")
		}
		launcherConfig.Bin(browserPath)
	}
	return launcherConfig.Launch()
}

func connectNativeBrowser(controlURL string) (*rod.Browser, error) {
	browser := rod.New().ControlURL(controlURL)
	if err := browser.Connect(); err != nil {
		return nil, err
	}
	return browser, nil
}

func browserUnavailableError(goos string, err error) error {
	prefix := "browser automation tidak tersedia"
	if strings.EqualFold(goos, "windows") {
		return fmt.Errorf("%s: install Chrome atau Edge, atau set AUTOKEREN_BROWSER_PATH ke chrome.exe/msedge.exe: %w", prefix, err)
	}
	return fmt.Errorf("%s: install browser Chromium-compatible atau set AUTOKEREN_BROWSER_PATH: %w", prefix, err)
}

func assertionExpression(kind, value string) (string, error) {
	literal, err := json.Marshal(value)
	if err != nil {
		return "", fmt.Errorf("encode assertion value: %w", err)
	}
	switch kind {
	case "visible_text":
		return fmt.Sprintf("() => Boolean(document.body && document.body.innerText.includes(%s))", literal), nil
	case "selector":
		return fmt.Sprintf("() => Boolean(document.querySelector(%s))", literal), nil
	default:
		return "", fmt.Errorf("unknown assertion kind: %s", kind)
	}
}

// Ensure context package is used to satisfy import checks
var _ context.Context
