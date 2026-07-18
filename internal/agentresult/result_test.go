package agentresult

import (
	"path/filepath"
	"reflect"
	"testing"
)

func TestBuildSeparatesFilesTestsAndBlockers(t *testing.T) {
	result := Build("selesai", []ToolEvidence{{Name: "write_file", OK: true, Path: "main.go"}, {Name: "run_shell", OK: true, Test: "go test"}, {Name: "run_shell", OK: false, Error: "exit 1"}})
	if !reflect.DeepEqual(result.FilesChanged, []string{"main.go"}) || len(result.Tests) != 1 || !reflect.DeepEqual(result.Blockers, []string{"exit 1"}) {
		t.Fatalf("unexpected result: %#v", result)
	}
}

func TestWriteAndRead(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nested", "result.json")
	expected := Build("selesai", nil)
	if err := Write(path, expected); err != nil {
		t.Fatal(err)
	}
	actual, err := Read(path)
	if err != nil || actual.Summary != expected.Summary {
		t.Fatalf("result=%#v err=%v", actual, err)
	}
}
