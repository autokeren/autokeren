package context

import (
	"strings"
	"sync"

	"github.com/autokeren/autokeren/internal/model"
)

type Store struct {
	mu          sync.RWMutex
	messages    []model.Message
	maxTokens   int
	autoCompact bool
	threshold   float64
	compactTail int
}

func New(maxTokens int, autoCompact bool, threshold float64) *Store {
	if maxTokens <= 0 {
		maxTokens = 262144
	}
	if threshold <= 0 || threshold >= 1 {
		threshold = 0.6
	}
	return &Store{maxTokens: maxTokens, autoCompact: autoCompact, threshold: threshold, compactTail: 6}
}
func (s *Store) Add(message model.Message) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.messages = append(s.messages, message)
	s.compactLocked()
}
func (s *Store) Messages() []model.Message {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return append([]model.Message(nil), s.messages...)
}
func (s *Store) Replace(messages []model.Message) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.messages = append([]model.Message(nil), messages...)
	s.compactLocked()
}
func (s *Store) TokenEstimate() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return estimate(s.messages)
}
func (s *Store) SetCompactTail(turns int) {
	if turns <= 0 {
		turns = 6
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.compactTail = turns
}
func (s *Store) Compact() (int, int, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	before := estimate(s.messages)
	changed := s.compactNowLocked()
	return before, estimate(s.messages), changed
}
func (s *Store) compactLocked() {
	if !s.autoCompact || estimate(s.messages) <= int(float64(s.maxTokens)*s.threshold) {
		return
	}
	s.compactNowLocked()
}
func (s *Store) compactNowLocked() bool {
	if len(s.messages) <= s.compactTail+1 {
		return false
	}
	tailStart := len(s.messages) - s.compactTail
	if tailStart < 1 {
		tailStart = 1
	}
	if tailStart <= 1 {
		return false
	}
	system := s.messages[0]
	tail := append([]model.Message(nil), s.messages[tailStart:]...)
	s.messages = append([]model.Message{system, {Role: "system", Content: "[context compacted] previous conversation summarized"}}, tail...)
	return true
}
func estimate(messages []model.Message) int {
	total := 0
	for _, m := range messages {
		total += len([]rune(strings.Join([]string{m.Role, m.Content, m.Name, m.ToolCallID}, " ")))/4 + len(m.ToolCalls)*8
	}
	return total
}
