package provider

import (
	"net/http"
	"testing"

	"github.com/autokeren/autokeren/internal/config"
)

func TestTargetsForConfigModes(t *testing.T) {
	tests := []struct {
		name      string
		configure func(*config.Config)
		endpoint  string
		key       string
		primary   string
	}{
		{
			name: "platform",
			configure: func(cfg *config.Config) {
				cfg.Auth.Mode = "platform"
				cfg.Auth.BaseURL = "https://platform.example"
				cfg.Auth.APIKey = "platform-key"
				cfg.Cloudflare.PrimaryModel = "@cf/moonshotai/kimi-k2.7-code"
			},
			endpoint: "https://platform.example/v1/chat/completions",
			key:      "platform-key",
			primary:  "kimi-code",
		},
		{
			name: "direct",
			configure: func(cfg *config.Config) {
				cfg.Auth.Mode = "direct"
				cfg.Cloudflare.AccountID = "account"
				cfg.Cloudflare.APIToken = "cf-token"
			},
			endpoint: "https://api.cloudflare.com/client/v4/accounts/account/ai/v1/chat/completions",
			key:      "cf-token",
			primary:  "kimi-code",
		},
		{
			name: "local",
			configure: func(cfg *config.Config) {
				cfg.Auth.Mode = "local"
				cfg.Auth.LocalEndpoint = "http://localhost:11434/"
			},
			endpoint: "http://localhost:11434/v1/chat/completions",
			primary:  "kimi-code",
		},
		{
			name: "openai",
			configure: func(cfg *config.Config) {
				cfg.Auth.Mode = "openai"
				cfg.Auth.OpenAIAPIKey = "openai-key"
				cfg.Cloudflare.PrimaryModel = "gpt-test"
			},
			endpoint: openAIEndpoint,
			key:      "openai-key",
			primary:  "gpt-test",
		},
		{
			name: "aistudio",
			configure: func(cfg *config.Config) {
				cfg.Auth.Mode = "aistudio"
				cfg.Auth.GeminiAPIKey = "gemini-key"
				cfg.Cloudflare.PrimaryModel = "kimi-code"
			},
			endpoint: geminiEndpoint,
			key:      "gemini-key",
			primary:  "gemini-3.5-pro",
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			cfg := config.Defaults()
			test.configure(&cfg)
			targets, err := TargetsForConfig(cfg, &http.Client{})
			if err != nil {
				t.Fatal(err)
			}
			if len(targets) == 0 || targets[0].ModelID != test.primary {
				t.Fatalf("targets = %#v", targets)
			}
			provider, ok := targets[0].Provider.(OpenAICompatible)
			if !ok || provider.Endpoint != test.endpoint || provider.APIKey != test.key {
				t.Fatalf("provider = %#v", provider)
			}
		})
	}
}

func TestTargetsForConfigRejectsUnsupportedMode(t *testing.T) {
	cfg := config.Defaults()
	cfg.Auth.Mode = "antigravity"
	if _, err := TargetsForConfig(cfg, &http.Client{}); err == nil {
		t.Fatal("expected unsupported mode error")
	}
}

func TestModelCatalogForConfig(t *testing.T) {
	tests := []struct {
		name      string
		configure func(*config.Config)
		url       string
		header    string
		key       string
	}{
		{
			name: "platform",
			configure: func(cfg *config.Config) {
				cfg.Auth.BaseURL = "https://platform.example/"
				cfg.Auth.APIKey = "platform-key"
			},
			url: "https://platform.example/v1/models", header: "Authorization", key: "platform-key",
		},
		{
			name: "local",
			configure: func(cfg *config.Config) {
				cfg.Auth.Mode = "local"
				cfg.Auth.LocalEndpoint = "http://localhost:11434/"
			},
			url: "http://localhost:11434/v1/models",
		},
		{
			name: "openai",
			configure: func(cfg *config.Config) {
				cfg.Auth.Mode = "openai"
				cfg.Auth.OpenAIAPIKey = "openai-key"
			},
			url: "https://api.openai.com/v1/models", header: "Authorization", key: "openai-key",
		},
		{
			name: "aistudio",
			configure: func(cfg *config.Config) {
				cfg.Auth.Mode = "aistudio"
				cfg.Auth.GeminiAPIKey = "gemini-key"
			},
			url: "https://generativelanguage.googleapis.com/v1beta/models", header: "x-goog-api-key", key: "gemini-key",
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			cfg := config.Defaults()
			test.configure(&cfg)
			catalog, ok := ModelCatalogForConfig(cfg)
			if !ok || catalog.URL != test.url || catalog.HeaderName != test.header || catalog.APIKey != test.key {
				t.Fatalf("catalog = %#v, ok=%v", catalog, ok)
			}
		})
	}
}
