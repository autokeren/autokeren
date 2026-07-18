package config

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestLoadDefaultsAndEnv(t *testing.T) {
	t.Setenv("AUTOKEREN_API_KEY", "env-key")
	cfg, err := Load(filepath.Join(t.TempDir(), "missing.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Auth.APIKey != "env-key" || cfg.Autokeren.ContextWindow != 262144 || !cfg.Autokeren.AutoSaveSession {
		t.Fatalf("unexpected config: %#v", cfg)
	}
}

func TestLoadYAML(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.yaml")
	data := []byte("auth:\n  mode: direct\ncloudflare:\n  primary_model: test-model\n")
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatal(err)
	}
	cfg, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Auth.Mode != "direct" || cfg.Cloudflare.PrimaryModel != "test-model" {
		t.Fatalf("unexpected config: %#v", cfg)
	}
}

func TestLoadKeepsConfiguredCredentialsOverEnvironment(t *testing.T) {
	t.Setenv("AUTOKEREN_API_KEY", "environment-key")
	t.Setenv("CLOUDFLARE_API_TOKEN", "environment-token")
	path := filepath.Join(t.TempDir(), "config.yaml")
	data := []byte("auth:\n  api_key: configured-key\ncloudflare:\n  api_token: configured-token\n")
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatal(err)
	}
	cfg, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Auth.APIKey != "configured-key" || cfg.Cloudflare.APIToken != "configured-token" {
		t.Fatalf("environment unexpectedly overrode config: %#v", cfg)
	}
}

func TestSaveRestrictsExistingConfigPermissions(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("Windows uses ACLs instead of POSIX file permissions")
	}
	path := filepath.Join(t.TempDir(), "config.yaml")
	if err := os.WriteFile(path, []byte("auth: {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := Save(path, Defaults()); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("permission config = %o, mau 600", info.Mode().Perm())
	}
}

func TestLoadUsesConfigDirectoryOverride(t *testing.T) {
	directory := t.TempDir()
	t.Setenv("AUTOKEREN_CONFIG_DIR", directory)
	path := filepath.Join(directory, "config.yaml")
	if err := Save(path, Config{Auth: Auth{Mode: "local", LocalEndpoint: "http://localhost:11434"}}); err != nil {
		t.Fatal(err)
	}
	cfg, err := Load("")
	if err != nil || cfg.Auth.Mode != "local" {
		t.Fatalf("config override tidak dimuat: %#v err=%v", cfg, err)
	}
}
