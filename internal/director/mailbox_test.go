package director

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/autokeren/autokeren/ghost"
	"github.com/autokeren/autokeren/internal/agentresult"
)

type fakeAgents struct {
	mu      sync.RWMutex
	items   []*ghost.GhostAgentInfo
	outputs map[int]string
}

func (f *fakeAgents) List() []*ghost.GhostAgentInfo {
	f.mu.RLock()
	defer f.mu.RUnlock()
	items := make([]*ghost.GhostAgentInfo, 0, len(f.items))
	for _, item := range f.items {
		copyItem := *item
		items = append(items, &copyItem)
	}
	return items
}
func (f *fakeAgents) Refresh() {}
func (f *fakeAgents) GetOutput(id int) string {
	f.mu.RLock()
	defer f.mu.RUnlock()
	return f.outputs[id]
}
func (f *fakeAgents) setStatus(id int, status string) {
	f.mu.Lock()
	defer f.mu.Unlock()
	for _, item := range f.items {
		if item.ID == id {
			item.Status = status
			return
		}
	}
}

func TestCollectPersistsBoundedWorkerResults(t *testing.T) {
	root := t.TempDir()
	agents := &fakeAgents{items: []*ghost.GhostAgentInfo{{ID: 2, Role: "reviewer", Status: "completed"}, {ID: 1, Role: "coder", Status: "failed", Error: "test gagal"}}, outputs: map[int]string{1: "detail gagal", 2: strings.Repeat("x", maxResultRunes+10)}}
	mailbox, err := New(root, agents).Collect([]int{2, 1})
	if err != nil {
		t.Fatal(err)
	}
	if len(mailbox.Entries) != 2 || mailbox.Entries[0].AgentID != 1 || !strings.Contains(mailbox.Entries[1].Output, "dipotong") {
		t.Fatalf("unexpected mailbox: %#v", mailbox)
	}
	if _, err := os.Stat(filepath.Join(root, ".autokeren", "agent-mailbox.json")); err != nil {
		t.Fatalf("mailbox not persisted: %v", err)
	}
}

func TestAwaitReturnsWhenWorkersFinish(t *testing.T) {
	agents := &fakeAgents{items: []*ghost.GhostAgentInfo{{ID: 1, Status: "completed"}}, outputs: map[int]string{1: "selesai"}}
	mailbox, err := New(t.TempDir(), agents).Await(context.Background(), []int{1}, time.Second)
	if err != nil || len(mailbox.Entries) != 1 || mailbox.Entries[0].Output != "selesai" {
		t.Fatalf("mailbox=%#v err=%v", mailbox, err)
	}
}

func TestMonitorBackgroundPersistsWorkerResultWithoutBlockingCaller(t *testing.T) {
	root := t.TempDir()
	agents := &fakeAgents{items: []*ghost.GhostAgentInfo{{ID: 1, Status: "running"}}, outputs: map[int]string{1: "selesai"}}
	coordinator := New(root, agents)
	coordinator.MonitorBackground([]int{1})
	agents.setStatus(1, "completed")
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		data, _ := os.ReadFile(filepath.Join(root, ".autokeren", "agent-mailbox.json"))
		if strings.Contains(string(data), "selesai") && strings.Contains(string(data), "completed") {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatal("background monitor did not persist completed worker result")
}

func TestConcurrentCollectionLeavesValidMailbox(t *testing.T) {
	root := t.TempDir()
	agents := &fakeAgents{items: []*ghost.GhostAgentInfo{{ID: 1, Status: "completed"}}, outputs: map[int]string{1: "selesai"}}
	coordinator := New(root, agents)
	var workers sync.WaitGroup
	for range 8 {
		workers.Add(1)
		go func() {
			defer workers.Done()
			if _, err := coordinator.Collect([]int{1}); err != nil {
				t.Error(err)
			}
		}()
	}
	workers.Wait()
	data, err := os.ReadFile(filepath.Join(root, ".autokeren", "agent-mailbox.json"))
	if err != nil || !strings.Contains(string(data), "completed") {
		t.Fatalf("mailbox akhir tidak valid: data=%q err=%v", data, err)
	}
}

func TestAwaitPersistsTimedOutWorkersWithoutLyingAboutTheirStatus(t *testing.T) {
	root := t.TempDir()
	agents := &fakeAgents{items: []*ghost.GhostAgentInfo{{ID: 4, Status: "running"}}, outputs: map[int]string{}}
	mailbox, err := New(root, agents).Await(context.Background(), []int{4}, time.Millisecond)
	if err == nil || mailbox.WaitStatus != "timed_out" || len(mailbox.PendingAgentIDs) != 1 || mailbox.PendingAgentIDs[0] != 4 || mailbox.Entries[0].Status != "running" {
		t.Fatalf("mailbox=%#v err=%v", mailbox, err)
	}
}

func TestCollectPrefersStructuredWorkerResult(t *testing.T) {
	root := t.TempDir()
	resultPath := filepath.Join(root, "worker.result.json")
	if err := agentresult.Write(resultPath, agentresult.Build("ringkasan worker", []agentresult.ToolEvidence{{Name: "write_file", OK: true, Path: "main.go"}})); err != nil {
		t.Fatal(err)
	}
	agents := &fakeAgents{items: []*ghost.GhostAgentInfo{{ID: 9, Status: "completed", ResultFile: resultPath}}, outputs: map[int]string{9: "log lama"}}
	mailbox, err := New(root, agents).Collect([]int{9})
	if err != nil || mailbox.Entries[0].Summary != "ringkasan worker" || len(mailbox.Entries[0].FilesChanged) != 1 || mailbox.Entries[0].Output != "" {
		t.Fatalf("mailbox=%#v err=%v", mailbox, err)
	}
}
