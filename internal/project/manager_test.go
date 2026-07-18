package project

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/autokeren/autokeren/ghost"
)

func TestManagerCreatesSwitchesAndAddsWorkers(t *testing.T) {
	manager := NewManager()
	if _, err := manager.New("demo"); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.AddWorker("reviewer", "review project"); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.New("other"); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.Switch("demo"); err != nil {
		t.Fatal(err)
	}
	project := manager.Active()
	if project == nil || project.Name != "demo" || len(project.Workers) != 1 || project.Workers[0].Status != "pending" {
		t.Fatalf("unexpected project: %#v", project)
	}
}

func TestManagerSchedulesDependencyDAGAndPreservesQueue(t *testing.T) {
	manager := NewManager()
	if _, err := manager.New("demo"); err != nil {
		t.Fatal(err)
	}
	for _, worker := range []struct {
		name string
		task string
	}{
		{name: "build", task: "build project"},
		{name: "deploy", task: "deploy project"},
		{name: "review", task: "review project"},
	} {
		if _, err := manager.AddWorker(worker.name, worker.task); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := manager.SetDependencies("deploy", []string{"build"}); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.SetDependencies("build", []string{"deploy"}); err == nil {
		t.Fatal("expected dependency cycle to be rejected")
	}
	project := manager.Active()
	if worker := project.Worker("build"); worker == nil || len(worker.DependsOn) != 0 {
		t.Fatalf("cycle rejection changed existing dependencies: %#v", worker)
	}

	ghosts := ghost.NewGhostManager(t.TempDir())
	ghosts.MaxAgents = 0
	schedule, err := manager.Tick(ghosts)
	if err != nil {
		t.Fatal(err)
	}
	if schedule.Queued != 0 || project.SchedulerEnabled {
		t.Fatalf("disabled scheduler must not queue work: %#v project=%#v", schedule, project)
	}
	schedule, err = manager.Run(ghosts)
	if err != nil {
		t.Fatal(err)
	}
	if schedule.Capacity != 0 || schedule.Launched != 0 || schedule.Queued != 3 {
		t.Fatalf("unexpected capacity-limited schedule: %#v", schedule)
	}

	manager.projects["demo"].worker("build").Status = "error"
	schedule, err = manager.Run(ghosts)
	if err != nil {
		t.Fatal(err)
	}
	if schedule.Blocked != 1 || manager.Active().Worker("deploy").Status != "blocked" {
		t.Fatalf("failed dependency did not block deploy: schedule=%#v project=%#v", schedule, manager.Active())
	}
	if _, err := manager.Retry("build"); err != nil {
		t.Fatal(err)
	}
	schedule, err = manager.Run(ghosts)
	if err != nil {
		t.Fatal(err)
	}
	if schedule.Queued != 3 || manager.Active().Worker("deploy").Status != "pending" {
		t.Fatalf("retry did not restore dependent queue: schedule=%#v project=%#v", schedule, manager.Active())
	}
}

func TestManagerRejectsRetryBeyondLimit(t *testing.T) {
	manager := NewManager()
	if _, err := manager.New("demo"); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.AddWorker("build", "build project"); err != nil {
		t.Fatal(err)
	}
	worker := manager.projects["demo"].worker("build")
	worker.Status = "error"
	worker.Attempts = worker.MaxAttempts
	if _, err := manager.Retry("build"); err == nil {
		t.Fatal("expected retry limit error")
	}
}

func TestPersistentManagerRestoresActiveProjectAndWorkers(t *testing.T) {
	root := t.TempDir()
	manager, err := NewPersistentManager(root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := manager.New("demo"); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.AddWorker("reviewer", "review project"); err != nil {
		t.Fatal(err)
	}
	if _, err := manager.New("other"); err != nil {
		t.Fatal(err)
	}
	restored, err := NewPersistentManager(root)
	if err != nil {
		t.Fatal(err)
	}
	if restored.ActiveName() != "other" || len(restored.List()) != 2 {
		t.Fatalf("unexpected restored state: active=%q projects=%#v", restored.ActiveName(), restored.List())
	}
	if _, err := restored.Switch("demo"); err != nil {
		t.Fatal(err)
	}
	project := restored.Active()
	if project == nil || len(project.Workers) != 1 || project.Workers[0].Task != "review project" {
		t.Fatalf("worker was not restored: %#v", project)
	}
	if _, err := os.Stat(filepath.Join(root, ".autokeren", "projects.json")); err != nil {
		t.Fatalf("project state was not written: %v", err)
	}
}
