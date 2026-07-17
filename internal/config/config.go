package config

import (
	"errors"
	"os"
	"path/filepath"

	"go.yaml.in/yaml/v3"
)

type Auth struct {
	Mode          string `yaml:"mode"`
	APIKey        string `yaml:"api_key"`
	BaseURL       string `yaml:"base_url"`
	GeminiAPIKey  string `yaml:"gemini_api_key"`
	OpenAIAPIKey  string `yaml:"openai_api_key"`
	LocalEndpoint string `yaml:"local_endpoint"`
}
type Cloudflare struct {
	AccountID      string  `yaml:"account_id"`
	APIToken       string  `yaml:"api_token"`
	PrimaryModel   string  `yaml:"primary_model"`
	SecondaryModel string  `yaml:"secondary_model"`
	MaxTokens      int     `yaml:"max_tokens"`
	Temperature    float64 `yaml:"temperature"`
	Timeout        float64 `yaml:"timeout"`
}
type Retry struct {
	MaxRetries              int     `yaml:"max_retries"`
	BaseDelay               float64 `yaml:"base_delay"`
	MaxDelay                float64 `yaml:"max_delay"`
	ExponentialBase         float64 `yaml:"exponential_base"`
	Jitter                  bool    `yaml:"jitter"`
	CircuitFailureThreshold int     `yaml:"circuit_failure_threshold"`
	CircuitOpenSeconds      int     `yaml:"circuit_open_seconds"`
}
type Autokeren struct {
	PlanMode             bool    `yaml:"plan_mode"`
	MaxIterations        int     `yaml:"max_iterations"`
	ShellTimeout         int     `yaml:"shell_timeout"`
	ContextWindow        int     `yaml:"context_window"`
	AutoCompact          bool    `yaml:"auto_compact"`
	AutoCompactThreshold float64 `yaml:"auto_compact_threshold"`
	AutoSaveSession      bool    `yaml:"auto_save_session"`
	Language             string  `yaml:"language"`
}
type MCPServer struct {
	Name    string            `yaml:"name"`
	Command []string          `yaml:"command"`
	Env     map[string]string `yaml:"env"`
	Enabled bool              `yaml:"enabled"`
}
type Config struct {
	Auth       Auth        `yaml:"auth"`
	Cloudflare Cloudflare  `yaml:"cloudflare"`
	Retry      Retry       `yaml:"retry"`
	Autokeren  Autokeren   `yaml:"autokeren"`
	MCPServers []MCPServer `yaml:"mcp_servers"`
}

var platformModelMap = map[string]string{
	"@cf/moonshotai/kimi-k2.7-code":           "kimi-code",
	"@cf/moonshotai/kimi-k2.6":                "kimi-2.6",
	"@cf/zai-org/glm-5.2":                     "glm-5.2",
	"@cf/zai-org/glm-4.7-flash":               "glm-flash",
	"@cf/meta/llama-4-scout-17b-16e-instruct": "llama-4-scout",
	"@cf/google/gemma-4-26b-a4b-it":           "gemma-4",
	"@cf/nvidia/nemotron-3-120b-a12b":         "nemotron",
}

func ResolveModel(modelID, mode string) string {
	if mode != "platform" || len(modelID) < 4 || modelID[:4] != "@cf/" {
		return modelID
	}
	if alias, ok := platformModelMap[modelID]; ok {
		return alias
	}
	return "kimi-2.6"
}

func Defaults() Config {
	return Config{Auth: Auth{Mode: "platform", BaseURL: "https://api.developers.autokeren.com", LocalEndpoint: "http://localhost:11434"}, Cloudflare: Cloudflare{PrimaryModel: "kimi-code", SecondaryModel: "kimi-2.6", MaxTokens: 8192, Temperature: 0.3, Timeout: 120}, Retry: Retry{MaxRetries: 5, BaseDelay: 1, MaxDelay: 60, ExponentialBase: 2, Jitter: true, CircuitFailureThreshold: 5, CircuitOpenSeconds: 30}, Autokeren: Autokeren{MaxIterations: 50, ShellTimeout: 180, ContextWindow: 262144, AutoCompact: true, AutoCompactThreshold: 0.6, AutoSaveSession: true}}
}

func Load(path string) (Config, error) {
	cfg := Defaults()
	if path == "" {
		if home, err := os.UserHomeDir(); err == nil {
			path = filepath.Join(home, ".config", "autokeren", "config.yaml")
		}
	}
	if path != "" {
		data, err := os.ReadFile(filepath.Clean(path))
		if err != nil && !errors.Is(err, os.ErrNotExist) {
			return Config{}, err
		}
		if err == nil && len(data) > 0 {
			if err := yaml.Unmarshal(data, &cfg); err != nil {
				return Config{}, err
			}
		}
	}
	applyEnv(&cfg)
	return cfg, nil
}

func applyEnv(cfg *Config) {
	if value := firstEnv("AUTOKEREN_API_KEY", "AK_API_KEY"); value != "" {
		cfg.Auth.APIKey = value
	}
	if value := firstEnv("CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT_ID"); value != "" {
		cfg.Cloudflare.AccountID = value
	}
	if value := firstEnv("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_API_KEY", "CF_API_TOKEN"); value != "" {
		cfg.Cloudflare.APIToken = value
	}
	if value := os.Getenv("GEMINI_API_KEY"); value != "" {
		cfg.Auth.GeminiAPIKey = value
	}
}
func firstEnv(keys ...string) string {
	for _, key := range keys {
		if value := os.Getenv(key); value != "" {
			return value
		}
	}
	return ""
}

func Save(path string, cfg Config) error {
	if path == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return err
		}
		path = filepath.Join(home, ".config", "autokeren", "config.yaml")
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	data, err := yaml.Marshal(cfg)
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Clean(path), data, 0o600)
}
