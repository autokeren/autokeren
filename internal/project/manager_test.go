package project

import (
	"os"
	"path/filepath"
	"testing"
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
