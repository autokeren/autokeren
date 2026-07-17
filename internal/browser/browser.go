package browser

import (
	"context"
	"fmt"
	"github.com/chromedp/chromedp"
	"sync"
	"time"
)

type Session struct {
	Name   string
	Ctx    context.Context
	Cancel context.CancelFunc
}
type Manager struct {
	mu       sync.Mutex
	sessions map[string]*Session
}

func NewManager() *Manager { return &Manager{sessions: make(map[string]*Session)} }
func (m *Manager) ensure(name string) (*Session, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if name == "" {
		name = "default"
	}
	if s := m.sessions[name]; s != nil {
		return s, nil
	}
	alloc, cancelAlloc := chromedp.NewExecAllocator(context.Background(), append(chromedp.DefaultExecAllocatorOptions[:], chromedp.Flag("headless", true))...)
	ctx, cancel := chromedp.NewContext(alloc)
	s := &Session{Name: name, Ctx: ctx, Cancel: func() { cancel(); cancelAlloc() }}
	if err := chromedp.Run(ctx); err != nil {
		s.Cancel()
		return nil, err
	}
	m.sessions[name] = s
	return s, nil
}
func (m *Manager) Run(ctx context.Context, name, action, target, value string) (any, error) {
	if action == "close" {
		return nil, m.Close(name)
	}
	s, err := m.ensure(name)
	if err != nil {
		return nil, err
	}
	opCtx, cancel := context.WithTimeout(s.Ctx, 30*time.Second)
	defer cancel()
	switch action {
	case "navigate":
		return nil, chromedp.Run(opCtx, chromedp.Navigate(target))
	case "text":
		var text string
		err := chromedp.Run(opCtx, chromedp.Text(target, &text, chromedp.ByQuery))
		return text, err
	case "click":
		return nil, chromedp.Run(opCtx, chromedp.Click(target, chromedp.ByQuery))
	case "type":
		return nil, chromedp.Run(opCtx, chromedp.SendKeys(target, value, chromedp.ByQuery))
	case "screenshot":
		var data []byte
		err := chromedp.Run(opCtx, chromedp.FullScreenshot(&data, 90))
		return data, err
	case "eval":
		var out any
		err := chromedp.Run(opCtx, chromedp.Evaluate(value, &out))
		return out, err
	case "status":
		return map[string]any{"session": name, "active": true}, nil
	default:
		return nil, fmt.Errorf("browser action tidak dikenal: %s", action)
	}
}
func (m *Manager) Close(name string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if name == "" {
		name = "default"
	}
	if s := m.sessions[name]; s != nil {
		s.Cancel()
		delete(m.sessions, name)
	}
	return nil
}
func (m *Manager) CloseAll() {
	m.mu.Lock()
	defer m.mu.Unlock()
	for name, s := range m.sessions {
		s.Cancel()
		delete(m.sessions, name)
	}
}
