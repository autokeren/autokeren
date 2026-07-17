package project

import "testing"

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
