package tool

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/autokeren/autokeren/internal/config"
)

func TestPublishAppSendsOnlyDeclaredModularFiles(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "src", "routes"), 0o700); err != nil {
		t.Fatal(err)
	}
	manifest := `{
  "schema_version": 1,
  "template": "web-app",
  "entrypoint": "src/worker.js",
  "capabilities": ["ai"],
  "migrations": [],
  "files": ["src/worker.js", "src/routes/home.js"]
}`
	if err := os.WriteFile(filepath.Join(root, appManifestDefaultPath), []byte(manifest), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "worker.js"), []byte(`import { home } from "./routes/home.js"; export default { fetch() { return home(); } };`), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "routes", "home.js"), []byte(`export function home() { return new Response("ok"); }`), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".env"), []byte("secret=do-not-upload"), 0o600); err != nil {
		t.Fatal(err)
	}
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.Method != http.MethodPost || request.URL.Path != "/v2/apps/publish" {
			t.Fatalf("unexpected request %s %s", request.Method, request.URL.Path)
		}
		if request.Header.Get("Authorization") != "Bearer ak_test" {
			t.Fatalf("missing authorization: %q", request.Header.Get("Authorization"))
		}
		var payload struct {
			Name  string          `json:"name"`
			Files []appSourceFile `json:"files"`
		}
		if err := json.NewDecoder(request.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		if payload.Name != "Toko Sepatu" || len(payload.Files) != 2 {
			t.Fatalf("unexpected publish payload: %#v", payload)
		}
		for _, file := range payload.Files {
			if file.Path == ".env" {
				t.Fatal("sensitive undeclared file was sent")
			}
		}
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`{"app_id":"app_123","release_id":"rel_123","status":"queued"}`))
	}))
	defer server.Close()

	result := (PublishApp{Config: config.Config{Auth: config.Auth{BaseURL: server.URL, APIKey: "ak_test"}}, Root: root}).Run(context.Background(), map[string]any{"name": "Toko Sepatu"}, nil)
	if !result.OK {
		t.Fatalf("publish failed: %#v", result)
	}
	data, ok := result.Output.(map[string]any)
	if !ok || data["release_id"] != "rel_123" {
		t.Fatalf("unexpected output: %#v", result.Output)
	}
}

func TestScaffoldAppCreatesManifestAndDatabaseMigration(t *testing.T) {
	root := t.TempDir()
	result := (ScaffoldApp{Root: root}).Run(context.Background(), map[string]any{"name": "Catatan", "template": "crud", "capabilities": []any{"database"}}, nil)
	if !result.OK {
		t.Fatalf("scaffold failed: %#v", result)
	}
	manifest, files, err := loadAppArtifact(root, appManifestDefaultPath)
	if err != nil {
		t.Fatal(err)
	}
	if manifest.Entrypoint != "src/worker.js" || len(manifest.Migrations) != 1 || len(files) != 3 {
		t.Fatalf("unexpected scaffold: %#v %#v", manifest, files)
	}
}

func TestScaffoldAppDoesNotPartiallyWriteWhenTargetExists(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "src"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "worker.js"), []byte("existing"), 0o600); err != nil {
		t.Fatal(err)
	}
	result := (ScaffoldApp{Root: root}).Run(context.Background(), map[string]any{"name": "Catatan"}, nil)
	if result.OK {
		t.Fatalf("expected scaffold to reject existing target: %#v", result)
	}
	if _, err := os.Stat(filepath.Join(root, appManifestDefaultPath)); !os.IsNotExist(err) {
		t.Fatalf("manifest should not be created after failed scaffold: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "src", "routes", "home.js")); !os.IsNotExist(err) {
		t.Fatalf("route should not be created after failed scaffold: %v", err)
	}
}

func TestLoadAppArtifactRejectsUndeclaredSensitivePath(t *testing.T) {
	root := t.TempDir()
	manifest := `{"schema_version":1,"entrypoint":"src/worker.js","capabilities":[],"migrations":[],"files":[".env","src/worker.js"]}`
	if err := os.MkdirAll(filepath.Join(root, "src"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, appManifestDefaultPath), []byte(manifest), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".env"), []byte("secret"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "worker.js"), []byte("export default {};"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, _, err := loadAppArtifact(root, appManifestDefaultPath); err == nil {
		t.Fatal("expected sensitive path rejection")
	}
}

func TestAppReleaseStatusWaitsForReadyRelease(t *testing.T) {
	requests := 0
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		requests++
		writer.Header().Set("Content-Type", "application/json")
		if requests == 1 {
			_, _ = writer.Write([]byte(`{"release_id":"rel_123","status":"deploying"}`))
			return
		}
		_, _ = writer.Write([]byte(`{"release_id":"rel_123","status":"ready","url":"https://app.example"}`))
	}))
	defer server.Close()
	result := (AppReleaseStatus{Config: config.Config{Auth: config.Auth{BaseURL: server.URL, APIKey: "ak_test"}}}).Run(context.Background(), map[string]any{"release_id": "rel_123", "wait_seconds": 1}, nil)
	if !result.OK || !releaseFinished(result.Output) || requests != 2 {
		t.Fatalf("unexpected release polling result: %#v requests=%d", result, requests)
	}
}
