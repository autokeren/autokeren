package cmd

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/autokeren/autokeren/internal/config"
	"github.com/autokeren/autokeren/internal/provider"
	"github.com/autokeren/autokeren/internal/tool"
)

const fallbackVersion = "0.12.2"

var (
	openAIModelsEndpoint   = "https://api.openai.com/v1/models"
	aiStudioModelsEndpoint = "https://generativelanguage.googleapis.com/v1beta/models"
	errLoginCancelled      = errors.New("login dibatalkan")
)

func runtimeVersion() string {
	if version := strings.TrimSpace(getenv("AUTOKEREN_VERSION")); version != "" {
		return version
	}
	return fallbackVersion
}

var getenv = os.Getenv

func showAbout(out io.Writer) {
	fmt.Fprintf(out, "autokeren v%s\nCloudflare-first agentic coding CLI untuk developer Indonesia.\nGitHub: https://github.com/autokeren/autokeren\nPlatform: https://developers.autokeren.com\n", runtimeVersion())
}

func runInit(in io.Reader, out io.Writer, path string) error {
	reader := bufio.NewReader(in)
	fmt.Fprintln(out, "Setup autokeren Go runtime")
	fmt.Fprintln(out, "1. Platform Autokeren (default)")
	fmt.Fprintln(out, "2. Cloudflare Direct")
	choice, err := promptLine(reader, out, "Mode [1]: ")
	if err != nil {
		return err
	}
	cfg := config.Defaults()
	if strings.TrimSpace(choice) == "2" {
		cfg.Auth.Mode = "direct"
		if cfg.Cloudflare.AccountID, err = promptLine(reader, out, "Cloudflare account ID: "); err != nil {
			return err
		}
		if cfg.Cloudflare.APIToken, err = promptLine(reader, out, "Cloudflare API token: "); err != nil {
			return err
		}
	} else {
		cfg.Auth.Mode = "platform"
		fmt.Fprintln(out, "Buka https://developers.autokeren.com/dashboard/keys untuk API key.")
		if cfg.Auth.APIKey, err = promptLine(reader, out, "API key: "); err != nil {
			return err
		}
	}
	provider.ApplyProviderDefaults(&cfg)
	if err := config.Save(path, cfg); err != nil {
		return err
	}
	fmt.Fprintf(out, "Config Go tersimpan di %s dengan permission 0600.\n", configPathForDisplay(path))
	return nil
}

func chooseModel(reader *bufio.Reader, out io.Writer, title string, models []string, defaultIndex int) (string, error) {
	if len(models) == 0 {
		return "", errors.New("daftar model kosong")
	}
	if defaultIndex < 0 || defaultIndex >= len(models) {
		defaultIndex = 0
	}
	fmt.Fprintf(out, "\n%s\n", title)
	for index, modelID := range models {
		fmt.Fprintf(out, "  %d. %s\n", index+1, modelID)
	}
	choice, err := promptLine(reader, out, fmt.Sprintf("Pilih [%d]: ", defaultIndex+1))
	if err != nil {
		return "", err
	}
	if choice == "" {
		return models[defaultIndex], nil
	}
	if strings.EqualFold(choice, "q") {
		return "", errLoginCancelled
	}
	index, err := strconv.Atoi(choice)
	if err != nil || index < 1 || index > len(models) {
		return "", fmt.Errorf("pilihan model %q tidak valid", choice)
	}
	return models[index-1], nil
}

func chooseProviderModels(reader *bufio.Reader, out io.Writer, cfg *config.Config, models []string) error {
	primary, err := chooseModel(reader, out, "Pilih model utama:", models, 0)
	if err != nil {
		return err
	}
	secondaryIndex := 0
	if len(models) > 1 {
		secondaryIndex = 1
	}
	secondary, err := chooseModel(reader, out, "Pilih model cadangan:", models, secondaryIndex)
	if err != nil {
		return err
	}
	cfg.Cloudflare.PrimaryModel = primary
	cfg.Cloudflare.SecondaryModel = secondary
	return nil
}

func fetchAIStudioModels(client *http.Client, apiKey string) []string {
	if client == nil {
		client = http.DefaultClient
	}
	request, err := http.NewRequestWithContext(context.Background(), http.MethodGet, aiStudioModelsEndpoint+"?key="+url.QueryEscape(apiKey), nil)
	if err != nil {
		return nil
	}
	response, err := client.Do(request)
	if err != nil {
		return nil
	}
	defer response.Body.Close()
	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return nil
	}
	var envelope struct {
		Models []struct {
			Name                       string   `json:"name"`
			SupportedGenerationMethods []string `json:"supportedGenerationMethods"`
		} `json:"models"`
	}
	if json.NewDecoder(io.LimitReader(response.Body, 2<<20)).Decode(&envelope) != nil {
		return nil
	}
	seen := make(map[string]bool, len(envelope.Models))
	models := make([]string, 0, len(envelope.Models))
	for _, item := range envelope.Models {
		supported := false
		for _, method := range item.SupportedGenerationMethods {
			if method == "generateContent" {
				supported = true
				break
			}
		}
		modelID := strings.TrimPrefix(strings.TrimSpace(item.Name), "models/")
		if supported && modelID != "" && !seen[modelID] {
			seen[modelID] = true
			models = append(models, modelID)
		}
	}
	return models
}

func runLogin(in io.Reader, out io.Writer, path string, client *http.Client) error {
	reader := bufio.NewReader(in)
	cfg, err := config.Load(path)
	if err != nil {
		return err
	}
	fmt.Fprintln(out, "AUTOKEREN LOGIN & CONFIGURATION WIZARD")
	fmt.Fprintln(out, "1. Platform Autokeren")
	fmt.Fprintln(out, "2. Cloudflare Direct")
	fmt.Fprintln(out, "3. OpenAI API")
	fmt.Fprintln(out, "4. Google AI Studio")
	fmt.Fprintln(out, "5. Local LLM")
	choice, err := promptLine(reader, out, "Pilih provider [1]: ")
	if err != nil {
		return err
	}
	if strings.TrimSpace(choice) == "" {
		choice = "1"
	}
	if strings.EqualFold(strings.TrimSpace(choice), "q") {
		return errLoginCancelled
	}
	modelOptions := []string(nil)
	switch choice {
	case "1":
		key, promptErr := promptLine(reader, out, "API key platform: ")
		if promptErr != nil {
			return promptErr
		}
		if !strings.HasPrefix(key, "ak_") {
			return errors.New("API key platform harus diawali ak_")
		}
		if err := validateHTTP(client, strings.TrimRight(cfg.Auth.BaseURL, "/")+"/v1/usage", "Authorization", "Bearer "+key); err != nil {
			return fmt.Errorf("validasi API key platform: %w", err)
		}
		cfg.Auth.Mode, cfg.Auth.APIKey = "platform", key
		modelOptions = provider.DefaultModelsForConfig(cfg)
	case "2":
		if cfg.Cloudflare.AccountID, err = promptLine(reader, out, "Cloudflare account ID: "); err != nil {
			return err
		}
		if cfg.Cloudflare.APIToken, err = promptLine(reader, out, "Cloudflare API token: "); err != nil {
			return err
		}
		if cfg.Cloudflare.AccountID == "" || cfg.Cloudflare.APIToken == "" {
			return errors.New("account ID dan API token Cloudflare wajib diisi")
		}
		cfg.Auth.Mode = "direct"
		modelOptions = provider.DefaultModelsForConfig(cfg)
	case "3":
		key, promptErr := promptLine(reader, out, "OpenAI API key: ")
		if promptErr != nil {
			return promptErr
		}
		if !strings.HasPrefix(key, "sk-") {
			return errors.New("OpenAI API key harus diawali sk-")
		}
		if err := validateHTTP(client, openAIModelsEndpoint, "Authorization", "Bearer "+key); err != nil {
			return fmt.Errorf("validasi OpenAI API key: %w", err)
		}
		cfg.Auth.Mode, cfg.Auth.OpenAIAPIKey = "openai", key
		modelOptions = provider.DefaultModelsForConfig(cfg)
	case "4":
		key, promptErr := promptLine(reader, out, "Google AI Studio API key: ")
		if promptErr != nil {
			return promptErr
		}
		if key == "" {
			return errors.New("Google AI Studio API key wajib diisi")
		}
		endpoint := aiStudioModelsEndpoint + "?key=" + url.QueryEscape(key)
		if err := validateHTTP(client, endpoint, "", ""); err != nil {
			return fmt.Errorf("validasi Google AI Studio API key: %w", err)
		}
		cfg.Auth.Mode, cfg.Auth.GeminiAPIKey = "aistudio", key
		modelOptions = fetchAIStudioModels(client, key)
		if len(modelOptions) == 0 {
			modelOptions = provider.DefaultModelsForConfig(cfg)
		}
	case "5":
		if cfg.Auth.LocalEndpoint, err = promptLine(reader, out, "Local endpoint [http://localhost:11434]: "); err != nil {
			return err
		}
		if cfg.Auth.LocalEndpoint == "" {
			cfg.Auth.LocalEndpoint = "http://localhost:11434"
		}
		if cfg.Cloudflare.PrimaryModel, err = promptLine(reader, out, "Model utama: "); err != nil {
			return err
		}
		if cfg.Cloudflare.SecondaryModel, err = promptLine(reader, out, "Model cadangan: "); err != nil {
			return err
		}
		cfg.Auth.Mode = "local"
	default:
		return errors.New("pilihan provider tidak dikenal")
	}
	if len(modelOptions) > 0 {
		if err := chooseProviderModels(reader, out, &cfg, modelOptions); err != nil {
			return err
		}
	}
	if err := config.Save(path, cfg); err != nil {
		return err
	}
	fmt.Fprintf(out, "Login berhasil. Provider aktif: %s\nModel utama: %s\nModel cadangan: %s\n", cfg.Auth.Mode, cfg.Cloudflare.PrimaryModel, cfg.Cloudflare.SecondaryModel)
	return nil
}

func validateHTTP(client *http.Client, endpoint, header, value string) error {
	if client == nil {
		client = http.DefaultClient
	}
	request, err := http.NewRequestWithContext(context.Background(), http.MethodGet, endpoint, nil)
	if err != nil {
		return err
	}
	if header != "" {
		request.Header.Set(header, value)
	}
	response, err := client.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return fmt.Errorf("HTTP %d", response.StatusCode)
	}
	return nil
}

func promptLine(reader *bufio.Reader, out io.Writer, label string) (string, error) {
	fmt.Fprint(out, label)
	value, err := reader.ReadString('\n')
	if err != nil && !errors.Is(err, io.EOF) {
		return "", err
	}
	if err == io.EOF && value == "" {
		return "", errors.New("input dibatalkan")
	}
	return strings.TrimSpace(value), nil
}

func runProof(root string, args []string, out io.Writer) error {
	if len(args) == 0 {
		return errors.New("format: --proof <list|replay|report|plan|record> ...")
	}
	action := args[0]
	toolArgs := map[string]any{"action": action}
	switch action {
	case "list":
	case "replay", "report":
		if len(args) < 2 {
			return fmt.Errorf("format: --proof %s <proof-id|file>", action)
		}
		toolArgs["proof_id"] = args[1]
	case "plan":
		parts := strings.Split(strings.Join(args[1:], " "), "|")
		if len(parts) < 2 || strings.TrimSpace(parts[0]) == "" {
			return errors.New("format: --proof plan <title> | <criterion1> [| <criterion2>]")
		}
		criteria := make([]any, 0, len(parts)-1)
		for _, part := range parts[1:] {
			if value := strings.TrimSpace(part); value != "" {
				criteria = append(criteria, value)
			}
		}
		if len(criteria) == 0 {
			return errors.New("minimal satu kriteria wajib diisi")
		}
		toolArgs["title"], toolArgs["criteria"] = strings.TrimSpace(parts[0]), criteria
	case "record":
		if len(args) < 4 {
			return errors.New("format: --proof record <proof-id> <nomor> <status> [evidence]")
		}
		number, err := strconv.Atoi(args[2])
		if err != nil {
			return errors.New("nomor kriteria harus angka")
		}
		toolArgs["proof_id"], toolArgs["criterion_num"], toolArgs["status"] = args[1], float64(number), args[3]
		if len(args) > 4 {
			toolArgs["evidence"] = strings.Join(args[4:], " ")
		}
	default:
		return fmt.Errorf("aksi proof tidak dikenal: %s", action)
	}
	result := (tool.Proof{Root: root}).Run(context.Background(), toolArgs, nil)
	if !result.OK {
		return errors.New(result.Error)
	}
	fprintln(out, result.Output)
	return nil
}

func fprintln(out io.Writer, value any) { _, _ = fmt.Fprintln(out, value) }

func configPathForDisplay(path string) string {
	if path != "" {
		return path
	}
	home, err := osUserHomeDir()
	if err != nil {
		return "config.yaml"
	}
	return filepath.Join(home, ".config", "autokeren", "config.yaml")
}

var osUserHomeDir = os.UserHomeDir
