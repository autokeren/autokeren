package director

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/autokeren/autokeren/ghost"
)

type fakeAgents struct {
	items   []*ghost.GhostAgentInfo
	outputs map[int]string
}

func (f *fakeAgents) List() []*ghost.GhostAgentInfo { return f.items }
func (f *fakeAgents) Refresh()                      {}
func (f *fakeAgents) GetOutput(id int) string       { return f.outputs[id] }

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

func TestAwaitPersistsTimedOutWorkersWithoutLyingAboutTheirStatus(t *testing.T) {
	root := t.TempDir()
	agents := &fakeAgents{items: []*ghost.GhostAgentInfo{{ID: 4, Status: "running"}}, outputs: map[int]string{}}
	mailbox, err := New(root, agents).Await(context.Background(), []int{4}, time.Millisecond)
	if err == nil || mailbox.WaitStatus != "timed_out" || len(mailbox.PendingAgentIDs) != 1 || mailbox.PendingAgentIDs[0] != 4 || mailbox.Entries[0].Status != "running" {
		t.Fatalf("mailbox=%#v err=%v", mailbox, err)
	}
}
