package tool

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/autokeren/autokeren/internal/config"
	"github.com/autokeren/autokeren/internal/safety"
)

const appManifestDefaultPath = "autokeren.app.json"

type PublishApp struct {
	Config config.Config
	Root   string
}

type AppReleaseStatus struct{ Config config.Config }

type ScaffoldApp struct {
	Root  string
	Guard *safety.Guard
}

type localAppManifest struct {
	SchemaVersion int      `json:"schema_version"`
	Template      string   `json:"template,omitempty"`
	Entrypoint    string   `json:"entrypoint"`
	Capabilities  []string `json:"capabilities"`
	Migrations    []string `json:"migrations"`
	Files         []string `json:"files"`
}

type platformAppManifest struct {
	SchemaVersion int      `json:"schema_version"`
	Template      string   `json:"template,omitempty"`
	Entrypoint    string   `json:"entrypoint"`
	Capabilities  []string `json:"capabilities"`
	Migrations    []string `json:"migrations"`
}

type appSourceFile struct {
	Path    string `json:"path"`
	Content string `json:"content"`
	SHA256  string `json:"sha256"`
}

func (t PublishApp) Definition() Definition {
	return Definition{Name: "publish_app", Description: "Publish a modular app through Autokeren Apps V2. Reads autokeren.app.json and its declared project files; users never need Cloudflare or Wrangler.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"name": map[string]any{"type": "string"}, "app_id": map[string]any{"type": "string"}, "manifest_path": map[string]any{"type": "string"}}, "required": []string{"name"}}}
}

func (t PublishApp) NeedsPermission(args map[string]any) (bool, string) {
	name, _ := args["name"].(string)
	return true, "publish aplikasi " + name + " melalui Autokeren"
}

func (t PublishApp) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	name, _ := args["name"].(string)
	appID, _ := args["app_id"].(string)
	manifestPath, _ := args["manifest_path"].(string)
	if manifestPath == "" {
		manifestPath = appManifestDefaultPath
	}
	if strings.TrimSpace(name) == "" {
		return Result{OK: false, Error: "name wajib"}
	}
	manifest, files, err := loadAppArtifact(t.Root, manifestPath)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	key, err := newIdempotencyKey()
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	payload := map[string]any{
		"name":            name,
		"idempotency_key": key,
		"manifest": platformAppManifest{
			SchemaVersion: manifest.SchemaVersion,
			Template:      manifest.Template,
			Entrypoint:    manifest.Entrypoint,
			Capabilities:  manifest.Capabilities,
			Migrations:    manifest.Migrations,
		},
		"files": files,
	}
	if appID != "" {
		payload["app_id"] = appID
	}
	return platformRequest(ctx, t.Config, "POST", "/v2/apps/publish", payload)
}

func (t AppReleaseStatus) Definition() Definition {
	return Definition{Name: "app_release_status", Description: "Read the current status and verification events of an Autokeren Apps V2 release.", Parameters: map[string]any{"type": "object", "properties": map[string]any{"release_id": map[string]any{"type": "string"}}, "required": []string{"release_id"}}}
}

func (t AppReleaseStatus) NeedsPermission(map[string]any) (bool, string) { return false, "" }

func (t AppReleaseStatus) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	releaseID, _ := args["release_id"].(string)
	if !strings.HasPrefix(releaseID, "rel_") {
		return Result{OK: false, Error: "release_id tidak valid"}
	}
	return platformRequest(ctx, t.Config, "GET", "/v2/releases/"+releaseID, nil)
}

func (t ScaffoldApp) Definition() Definition {
	return Definition{Name: "scaffold_app", Description: "Create a safe modular Autokeren Apps V2 starter: manifest, Worker entry point, route module, and optional D1 migration. Use this before writing app-specific code.", RequiresPermission: true, Parameters: map[string]any{"type": "object", "properties": map[string]any{"name": map[string]any{"type": "string"}, "template": map[string]any{"type": "string"}, "capabilities": map[string]any{"type": "array", "items": map[string]any{"type": "string", "enum": []string{"database", "storage", "ai"}}}}, "required": []string{"name"}}}
}

func (t ScaffoldApp) NeedsPermission(args map[string]any) (bool, string) {
	name, _ := args["name"].(string)
	return true, "membuat struktur aplikasi modular " + name
}

func (t ScaffoldApp) Run(ctx context.Context, args map[string]any, _ Emitter) Result {
	select {
	case <-ctx.Done():
		return Result{OK: false, Error: ctx.Err().Error()}
	default:
	}
	name, _ := args["name"].(string)
	if strings.TrimSpace(name) == "" {
		return Result{OK: false, Error: "name wajib"}
	}
	template, _ := args["template"].(string)
	if template == "" {
		template = "web-app"
	}
	capabilities, err := appCapabilities(args["capabilities"])
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	manifestTarget, err := safePath(t.Root, appManifestDefaultPath)
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	if _, err := os.Stat(manifestTarget); err == nil {
		return Result{OK: false, Error: appManifestDefaultPath + " sudah ada; scaffold tidak menimpa project yang ada"}
	} else if !os.IsNotExist(err) {
		return Result{OK: false, Error: err.Error()}
	}
	files := []string{"src/worker.js", "src/routes/home.js"}
	migrations := []string{}
	if containsCapability(capabilities, "database") {
		migrations = append(migrations, "migrations/0001_initial.sql")
		files = append(files, migrations[0])
	}
	manifest := localAppManifest{SchemaVersion: 1, Template: template, Entrypoint: "src/worker.js", Capabilities: capabilities, Migrations: migrations, Files: files}
	manifestData, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return Result{OK: false, Error: err.Error()}
	}
	contents := map[string]string{
		appManifestDefaultPath: string(manifestData) + "\n",
		"src/worker.js":        "import { home } from \"./routes/home.js\";\n\nexport default {\n  async fetch(request, env) {\n    const url = new URL(request.url);\n    if (url.pathname === \"/\") return home(env);\n    return new Response(\"Tidak ditemukan\", { status: 404 });\n  },\n};\n",
		"src/routes/home.js":   "export function home() {\n  return new Response(\"Aplikasi Autokeren siap dibangun.\", {\n    headers: { \"content-type\": \"text/plain; charset=utf-8\" },\n  });\n}\n",
	}
	if containsCapability(capabilities, "database") {
		contents["migrations/0001_initial.sql"] = "CREATE TABLE IF NOT EXISTS app_items (\n  id INTEGER PRIMARY KEY,\n  name TEXT NOT NULL,\n  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP\n);\n"
	}
	paths := append([]string{appManifestDefaultPath}, files...)
	for _, path := range paths {
		target, pathErr := safePath(t.Root, path)
		if pathErr != nil {
			return Result{OK: false, Error: pathErr.Error()}
		}
		if err := safety.ValidateWriteTarget(target); err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		if _, statErr := os.Stat(target); statErr == nil {
			return Result{OK: false, Error: path + " sudah ada; scaffold tidak menimpa file"}
		} else if !os.IsNotExist(statErr) {
			return Result{OK: false, Error: statErr.Error()}
		}
		if _, guardErr := validateWrite(t.Guard, path, contents[path]); guardErr != nil {
			return Result{OK: false, Error: guardErr.Error()}
		}
	}
	for _, path := range paths {
		content := contents[path]
		target, _ := safePath(t.Root, path)
		if err := writeAtomic(target, []byte(content)); err != nil {
			return Result{OK: false, Error: err.Error()}
		}
		if t.Guard != nil {
			t.Guard.RecordWrite(path, content)
		}
	}
	return Result{OK: true, Output: map[string]any{"manifest_path": appManifestDefaultPath, "files": files, "next": "Tulis fitur aplikasi secara modular, jalankan test, lalu panggil publish_app."}}
}

func loadAppArtifact(root, manifestPath string) (localAppManifest, []appSourceFile, error) {
	var manifest localAppManifest
	target, err := safePath(root, manifestPath)
	if err != nil {
		return manifest, nil, err
	}
	if blocked, reason := safety.ValidateRead(target); blocked {
		return manifest, nil, fmt.Errorf("%s", reason)
	}
	data, err := os.ReadFile(target)
	if err != nil {
		return manifest, nil, err
	}
	if err := json.Unmarshal(data, &manifest); err != nil {
		return manifest, nil, fmt.Errorf("manifest tidak valid: %w", err)
	}
	if manifest.SchemaVersion != 1 || manifest.Entrypoint == "" {
		return manifest, nil, fmt.Errorf("manifest harus memiliki schema_version 1 dan entrypoint")
	}
	if !containsString(manifest.Files, manifest.Entrypoint) {
		return manifest, nil, fmt.Errorf("manifest files harus memuat entrypoint")
	}
	for _, migration := range manifest.Migrations {
		if !containsString(manifest.Files, migration) {
			return manifest, nil, fmt.Errorf("manifest files harus memuat migration %s", migration)
		}
	}
	if _, err := appCapabilities(manifest.Capabilities); err != nil {
		return manifest, nil, err
	}
	files := make([]appSourceFile, 0, len(manifest.Files))
	seen := make(map[string]struct{})
	for _, path := range manifest.Files {
		if !safeAppRelativePath(path) {
			return manifest, nil, fmt.Errorf("path manifest tidak aman: %s", path)
		}
		if _, ok := seen[path]; ok {
			return manifest, nil, fmt.Errorf("path manifest duplikat: %s", path)
		}
		seen[path] = struct{}{}
		target, pathErr := safePath(root, path)
		if pathErr != nil {
			return manifest, nil, pathErr
		}
		if blocked, reason := safety.ValidateRead(target); blocked {
			return manifest, nil, fmt.Errorf("%s", reason)
		}
		info, statErr := os.Lstat(target)
		if statErr != nil {
			return manifest, nil, statErr
		}
		if info.Mode()&fs.ModeSymlink != 0 || !info.Mode().IsRegular() {
			return manifest, nil, fmt.Errorf("path manifest harus file regular: %s", path)
		}
		content, readErr := os.ReadFile(target)
		if readErr != nil {
			return manifest, nil, readErr
		}
		if len(content) > 256*1024 {
			return manifest, nil, fmt.Errorf("file terlalu besar: %s", path)
		}
		digest := sha256.Sum256(content)
		files = append(files, appSourceFile{Path: path, Content: string(content), SHA256: hex.EncodeToString(digest[:])})
	}
	sort.Slice(files, func(i, j int) bool { return files[i].Path < files[j].Path })
	return manifest, files, nil
}

func newIdempotencyKey() (string, error) {
	data := make([]byte, 16)
	if _, err := rand.Read(data); err != nil {
		return "", err
	}
	return "cli-" + hex.EncodeToString(data), nil
}

func appCapabilities(value any) ([]string, error) {
	if value == nil {
		return []string{}, nil
	}
	items, ok := value.([]any)
	if !ok {
		if stringsValue, stringsOK := value.([]string); stringsOK {
			items = make([]any, len(stringsValue))
			for index, item := range stringsValue {
				items[index] = item
			}
		} else {
			return nil, fmt.Errorf("capabilities harus berupa daftar")
		}
	}
	allowed := map[string]bool{"database": true, "storage": true, "ai": true}
	result := make([]string, 0, len(items))
	seen := make(map[string]bool)
	for _, item := range items {
		capability, ok := item.(string)
		if !ok || !allowed[capability] {
			return nil, fmt.Errorf("capability tidak didukung")
		}
		if !seen[capability] {
			seen[capability] = true
			result = append(result, capability)
		}
	}
	sort.Strings(result)
	return result, nil
}

func containsCapability(capabilities []string, target string) bool {
	return containsString(capabilities, target)
}

func containsString(items []string, target string) bool {
	for _, item := range items {
		if item == target {
			return true
		}
	}
	return false
}

func safeAppRelativePath(path string) bool {
	cleaned := filepath.ToSlash(filepath.Clean(path))
	if path == "" || filepath.IsAbs(path) || cleaned != path || strings.HasPrefix(path, ".") || strings.Contains(path, "//") {
		return false
	}
	for _, part := range strings.Split(path, "/") {
		if part == "." || part == ".." || part == ".env" || part == ".git" || part == ".ssh" || part == "node_modules" {
			return false
		}
	}
	return true
}
