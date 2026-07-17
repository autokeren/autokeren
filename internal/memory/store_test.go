package memory

import (
	"os"
	"strings"
	"testing"
)

func TestStoreRetrievesRelevantNotes(t *testing.T) {
	store := New(t.TempDir())
	for _, note := range []struct{ section, text string }{
		{"build", "Jalankan go test ./... sebelum commit router."},
		{"deploy", "Worker production memakai wrangler deploy."},
		{"debug", "Router retry memakai Retry-After untuk error 429."},
	} {
		if err := store.Append(note.section, note.text); err != nil {
			t.Fatal(err)
		}
	}
	results := store.Search("bagaimana retry router saat 429", 2)
	if len(results) == 0 || !strings.Contains(results[0], "Router retry") {
		t.Fatalf("unexpected results: %#v", results)
	}
	context := store.Context("retry router", 2)
	if !strings.Contains(context, "Memori proyek relevan") || !strings.Contains(context, "Retry-After") {
		t.Fatalf("unexpected context: %s", context)
	}
}

func TestStoreDoesNotTreatHeadingsAsNotes(t *testing.T) {
	store := New(t.TempDir())
	if err := store.Append("build", "Gunakan pytest untuk test Python."); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(store.Path(), []byte("# Heading\n- [build] Gunakan pytest untuk test Python.\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	results := store.Search("pytest", 2)
	if len(results) != 1 || strings.Contains(results[0], "Heading") {
		t.Fatalf("unexpected results: %#v", results)
	}
}
