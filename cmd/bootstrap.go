package cmd

import (
	"bufio"
	"context"
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

const fallbackVersion = "0.12.0"

var (
	openAIModelsEndpoint   = "https://api.openai.com/v1/models"
	aiStudioModelsEndpoint = "https://generativelanguage.googleapis.com/v1beta/models"
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

func runLogin(in io.Reader, out io.Writer, path string, client *http.Client) error {
	reader := bufio.NewReader(in)
	cfg, err := config.Load(path)
	if err != nil {
		return err
	}
	fmt.Fprintln(out, "Login Autokeren Go runtime")
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
	provider.ApplyProviderDefaults(&cfg)
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
