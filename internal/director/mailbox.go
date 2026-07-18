package director

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/autokeren/autokeren/ghost"
	"github.com/autokeren/autokeren/internal/agentresult"
)

const maxResultRunes = 4000

type AgentSource interface {
	List() []*ghost.GhostAgentInfo
	Refresh()
	GetOutput(int) string
}

type MailboxEntry struct {
	AgentID      int                        `json:"agent_id"`
	Role         string                     `json:"role,omitempty"`
	Status       string                     `json:"status"`
	Output       string                     `json:"output,omitempty"`
	Summary      string                     `json:"summary,omitempty"`
	FilesChanged []string                   `json:"files_changed,omitempty"`
	Tests        []agentresult.ToolEvidence `json:"tests,omitempty"`
	Tools        []agentresult.ToolEvidence `json:"tools,omitempty"`
	Blockers     []string                   `json:"blockers,omitempty"`
	Error        string                     `json:"error,omitempty"`
	FinishedAt   time.Time                  `json:"finished_at,omitempty"`
}

type Mailbox struct {
	UpdatedAt       time.Time      `json:"updated_at"`
	WaitStatus      string         `json:"wait_status"`
	PendingAgentIDs []int          `json:"pending_agent_ids,omitempty"`
	Entries         []MailboxEntry `json:"entries"`
}

type Coordinator struct {
	root      string
	agents    AgentSource
	persistMu sync.Mutex
}

func New(root string, agents AgentSource) *Coordinator {
	return &Coordinator{root: root, agents: agents}
}

func (c *Coordinator) Await(ctx context.Context, ids []int, timeout time.Duration) (Mailbox, error) {
	if c == nil || c.agents == nil {
		return Mailbox{}, fmt.Errorf("director mailbox tidak tersedia")
	}
	if timeout <= 0 {
		timeout = 5 * time.Minute
	}
	if timeout > 10*time.Minute {
		timeout = 10 * time.Minute
	}
	deadline := time.NewTimer(timeout)
	defer deadline.Stop()
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	for {
		c.agents.Refresh()
		mailbox, pending, err := c.collect(ids)
		if err != nil {
			return Mailbox{}, err
		}
		if !pending {
			return mailbox, nil
		}
		select {
		case <-ctx.Done():
			return Mailbox{}, ctx.Err()
		case <-deadline.C:
			mailbox.WaitStatus = "timed_out"
			mailbox.PendingAgentIDs = pendingAgentIDs(mailbox.Entries)
			if persistErr := c.persist(mailbox); persistErr != nil {
				return Mailbox{}, persistErr
			}
			return mailbox, fmt.Errorf("menunggu hasil agent melewati batas waktu")
		case <-ticker.C:
		}
	}
}

func (c *Coordinator) Collect(ids []int) (Mailbox, error) {
	if c == nil || c.agents == nil {
		return Mailbox{}, fmt.Errorf("director mailbox tidak tersedia")
	}
	c.agents.Refresh()
	mailbox, _, err := c.collect(ids)
	return mailbox, err
}

func (c *Coordinator) MonitorBackground(ids []int) {
	if c == nil || c.agents == nil || len(ids) == 0 {
		return
	}
	tracked := append([]int(nil), ids...)
	go func() {
		ticker := time.NewTicker(500 * time.Millisecond)
		defer ticker.Stop()
		for {
			c.agents.Refresh()
			_, pending, err := c.collect(tracked)
			if err != nil || !pending {
				return
			}
			<-ticker.C
		}
	}()
}

func (c *Coordinator) collect(ids []int) (Mailbox, bool, error) {
	requested := map[int]struct{}{}
	for _, id := range ids {
		if id > 0 {
			requested[id] = struct{}{}
		}
	}
	entries := make([]MailboxEntry, 0)
	pending := false
	for _, info := range c.agents.List() {
		if len(requested) > 0 {
			if _, ok := requested[info.ID]; !ok {
				continue
			}
		}
		entry := MailboxEntry{AgentID: info.ID, Role: info.Role, Status: info.Status, Error: info.Error, FinishedAt: info.FinishedAt}
		if info.Status == "running" || info.Status == "unknown" {
			pending = true
		}
		if info.Status != "running" && info.Status != "unknown" {
			if result, resultErr := agentresult.Read(info.ResultFile); resultErr == nil {
				entry.Summary = limitRunes(result.Summary, maxResultRunes)
				entry.FilesChanged = result.FilesChanged
				entry.Tests = result.Tests
				entry.Tools = result.Tools
				entry.Blockers = result.Blockers
			} else {
				entry.Output = limitRunes(strings.TrimSpace(c.agents.GetOutput(info.ID)), maxResultRunes)
			}
		}
		entries = append(entries, entry)
	}
	if len(requested) > 0 && len(entries) != len(requested) {
		return Mailbox{}, false, fmt.Errorf("satu atau lebih agent tidak ditemukan")
	}
	sort.Slice(entries, func(left, right int) bool { return entries[left].AgentID < entries[right].AgentID })
	mailbox := Mailbox{UpdatedAt: time.Now().UTC(), WaitStatus: "ready", Entries: entries}
	if pending {
		mailbox.WaitStatus = "pending"
		mailbox.PendingAgentIDs = pendingAgentIDs(entries)
	}
	if err := c.persist(mailbox); err != nil {
		return Mailbox{}, false, err
	}
	return mailbox, pending, nil
}

func pendingAgentIDs(entries []MailboxEntry) []int {
	ids := make([]int, 0)
	for _, entry := range entries {
		if entry.Status == "running" || entry.Status == "unknown" {
			ids = append(ids, entry.AgentID)
		}
	}
	return ids
}

func (c *Coordinator) persist(mailbox Mailbox) error {
	if c.root == "" {
		return nil
	}
	c.persistMu.Lock()
	defer c.persistMu.Unlock()
	path := filepath.Join(c.root, ".autokeren", "agent-mailbox.json")
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return fmt.Errorf("buat direktori mailbox: %w", err)
	}
	data, err := json.MarshalIndent(mailbox, "", "  ")
	if err != nil {
		return fmt.Errorf("serialisasi mailbox: %w", err)
	}
	temporary, err := os.CreateTemp(filepath.Dir(path), ".agent-mailbox-")
	if err != nil {
		return fmt.Errorf("buat file mailbox sementara: %w", err)
	}
	temporaryPath := temporary.Name()
	defer os.Remove(temporaryPath)
	if err := temporary.Chmod(0o600); err != nil {
		_ = temporary.Close()
		return fmt.Errorf("atur izin mailbox sementara: %w", err)
	}
	if _, err := temporary.Write(data); err != nil {
		_ = temporary.Close()
		return fmt.Errorf("tulis mailbox: %w", err)
	}
	if err := temporary.Close(); err != nil {
		return fmt.Errorf("tutup mailbox sementara: %w", err)
	}
	if err := os.Rename(temporaryPath, path); err != nil {
		return fmt.Errorf("simpan mailbox: %w", err)
	}
	return nil
}

func limitRunes(value string, limit int) string {
	runes := []rune(value)
	if len(runes) <= limit {
		return value
	}
	return string(runes[:limit]) + "\n[output dipotong untuk context director]"
}
