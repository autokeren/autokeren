package provider

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/autokeren/autokeren/internal/config"
)

const (
	cloudflareAPIBase = "https://api.cloudflare.com/client/v4"
	openAIEndpoint    = "https://api.openai.com/v1/chat/completions"
	geminiEndpoint    = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
)

type ModelCatalogRequest struct {
	URL        string
	HeaderName string
	APIKey     string
}

func DefaultModelsForConfig(cfg config.Config) []string {
	switch strings.ToLower(strings.TrimSpace(cfg.Auth.Mode)) {
	case "direct":
		return []string{"@cf/moonshotai/kimi-k2.7-code", "@cf/moonshotai/kimi-k2.6", "@cf/zai-org/glm-5.2", "@cf/zai-org/glm-4.7-flash"}
	case "openai":
		return []string{"gpt-5.6", "gpt-5.6-mini", "gpt-4o", "gpt-4o-mini"}
	case "aistudio":
		return []string{"gemini-3.5-flash", "gemini-3.5-pro"}
	case "local":
		return uniqueModelIDs([]string{cfg.Cloudflare.PrimaryModel, cfg.Cloudflare.SecondaryModel})
	default:
		return []string{"kimi-code", "kimi-2.6", "glm-5.2", "glm-flash", "llama-4-scout", "gemma-4", "nemotron"}
	}
}

func ApplyProviderDefaults(cfg *config.Config) {
	if cfg == nil || strings.EqualFold(strings.TrimSpace(cfg.Auth.Mode), "local") {
		return
	}
	models := DefaultModelsForConfig(*cfg)
	if len(models) == 0 {
		return
	}
	cfg.Cloudflare.PrimaryModel = models[0]
	if len(models) > 1 {
		cfg.Cloudflare.SecondaryModel = models[1]
	} else {
		cfg.Cloudflare.SecondaryModel = ""
	}
}

func ValidateModelForConfig(cfg config.Config, modelID string) error {
	modelID = strings.TrimSpace(modelID)
	if modelID == "" {
		return fmt.Errorf("model belum diisi")
	}
	mode := strings.ToLower(strings.TrimSpace(cfg.Auth.Mode))
	lower := strings.ToLower(strings.TrimPrefix(modelID, "models/"))
	switch mode {
	case "direct":
		if !strings.HasPrefix(modelID, "@cf/") {
			return fmt.Errorf("model %q bukan model Cloudflare Direct; pilih model @cf/...", modelID)
		}
	case "openai":
		if strings.HasPrefix(modelID, "@cf/") || strings.HasPrefix(lower, "kimi") || strings.HasPrefix(lower, "glm") || strings.HasPrefix(lower, "gemini") || strings.HasPrefix(lower, "llama") || strings.HasPrefix(lower, "gemma") || strings.HasPrefix(lower, "nemotron") {
			return fmt.Errorf("model %q bukan model OpenAI; jalankan autokeren --login untuk memilih model OpenAI", modelID)
		}
	case "aistudio":
		if !strings.HasPrefix(lower, "gemini") {
			return fmt.Errorf("model %q bukan model Google AI Studio; pilih model Gemini", modelID)
		}
	}
	return nil
}

func ModelCatalogForConfig(cfg config.Config) (ModelCatalogRequest, bool) {
	switch strings.ToLower(strings.TrimSpace(cfg.Auth.Mode)) {
	case "", "platform":
		base := strings.TrimRight(strings.TrimSpace(cfg.Auth.BaseURL), "/")
		if base == "" {
			return ModelCatalogRequest{}, false
		}
		return ModelCatalogRequest{URL: base + "/v1/models", HeaderName: "Authorization", APIKey: cfg.Auth.APIKey}, true
	case "local":
		base := strings.TrimRight(strings.TrimSpace(cfg.Auth.LocalEndpoint), "/")
		if base == "" {
			return ModelCatalogRequest{}, false
		}
		return ModelCatalogRequest{URL: base + "/v1/models"}, true
	case "openai":
		return ModelCatalogRequest{URL: "https://api.openai.com/v1/models", HeaderName: "Authorization", APIKey: cfg.Auth.OpenAIAPIKey}, true
	case "aistudio":
		return ModelCatalogRequest{URL: "https://generativelanguage.googleapis.com/v1beta/models", HeaderName: "x-goog-api-key", APIKey: cfg.Auth.GeminiAPIKey}, true
	default:
		return ModelCatalogRequest{}, false
	}
}

func TargetsForConfig(cfg config.Config, client *http.Client) ([]Target, error) {
	mode := strings.ToLower(strings.TrimSpace(cfg.Auth.Mode))
	primary := cfg.Cloudflare.PrimaryModel
	secondary := cfg.Cloudflare.SecondaryModel
	endpoint := ""
	apiKey := ""
	switch mode {
	case "", "platform":
		endpoint = chatCompletionsEndpoint(cfg.Auth.BaseURL)
		apiKey = cfg.Auth.APIKey
		primary = config.ResolveModel(primary, "platform")
		secondary = config.ResolveModel(secondary, "platform")
		if apiKey == "" {
			return nil, fmt.Errorf("AUTOKEREN_API_KEY belum diisi untuk mode platform")
		}
	case "direct":
		if cfg.Cloudflare.AccountID == "" || cfg.Cloudflare.APIToken == "" {
			return nil, fmt.Errorf("account_id dan api_token Cloudflare wajib diisi untuk mode direct")
		}
		endpoint = strings.TrimRight(cloudflareAPIBase, "/") + "/accounts/" + cfg.Cloudflare.AccountID + "/ai/v1/chat/completions"
		apiKey = cfg.Cloudflare.APIToken
	case "local":
		endpoint = chatCompletionsEndpoint(cfg.Auth.LocalEndpoint)
		if endpoint == "" {
			return nil, fmt.Errorf("local_endpoint belum diisi untuk mode local")
		}
	case "openai":
		apiKey = cfg.Auth.OpenAIAPIKey
		if apiKey == "" {
			return nil, fmt.Errorf("OPENAI_API_KEY belum diisi untuk mode openai")
		}
		endpoint = openAIEndpoint
	case "aistudio":
		apiKey = cfg.Auth.GeminiAPIKey
		if apiKey == "" {
			return nil, fmt.Errorf("GEMINI_API_KEY belum diisi untuk mode aistudio")
		}
		endpoint = geminiEndpoint
		primary = resolveAIStudioModel(primary)
		secondary = resolveAIStudioModel(secondary)
	case "antigravity":
		return nil, fmt.Errorf("mode antigravity disembunyikan dan tidak didukung oleh runtime Go")
	default:
		return nil, fmt.Errorf("mode autentikasi %q tidak didukung oleh runtime Go", cfg.Auth.Mode)
	}
	if err := ValidateModelForConfig(cfg, primary); err != nil {
		return nil, err
	}
	if strings.TrimSpace(secondary) != "" {
		if err := ValidateModelForConfig(cfg, secondary); err != nil {
			return nil, err
		}
	}
	base := OpenAICompatible{Endpoint: endpoint, APIKey: apiKey, Client: client}
	targets := uniqueTargets([]Target{{ModelID: primary, Provider: base}, {ModelID: secondary, Provider: base}})
	if len(targets) == 0 {
		return nil, fmt.Errorf("model utama belum diisi")
	}
	return targets, nil
}

func uniqueModelIDs(ids []string) []string {
	seen := make(map[string]bool, len(ids))
	output := make([]string, 0, len(ids))
	for _, id := range ids {
		id = strings.TrimSpace(id)
		if id == "" || seen[id] {
			continue
		}
		seen[id] = true
		output = append(output, id)
	}
	return output
}

func chatCompletionsEndpoint(base string) string {
	base = strings.TrimRight(strings.TrimSpace(base), "/")
	if base == "" {
		return ""
	}
	if strings.HasSuffix(base, "/v1/chat/completions") {
		return base
	}
	return base + "/v1/chat/completions"
}

func uniqueTargets(targets []Target) []Target {
	seen := map[string]struct{}{}
	output := make([]Target, 0, len(targets))
	for _, target := range targets {
		if strings.TrimSpace(target.ModelID) == "" {
			continue
		}
		if _, exists := seen[target.ModelID]; exists {
			continue
		}
		seen[target.ModelID] = struct{}{}
		output = append(output, target)
	}
	return output
}

func resolveAIStudioModel(modelID string) string {
	modelID = strings.TrimSpace(modelID)
	if strings.Contains(strings.ToLower(modelID), "gemini") {
		return modelID
	}
	if strings.Contains(strings.ToLower(modelID), "code") || strings.Contains(strings.ToLower(modelID), "pro") {
		return "gemini-3.5-pro"
	}
	return "gemini-3.5-flash"
}
