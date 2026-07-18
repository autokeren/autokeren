package cmd

import (
	"bytes"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/autokeren/autokeren/internal/config"
)

func TestRunLoginPlatformSavesValidatedKey(t *testing.T) {
	t.Parallel()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/v1/usage" {
			t.Fatalf("unexpected path: %s", request.URL.Path)
		}
		if request.Header.Get("Authorization") != "Bearer ak_test_key" {
			t.Fatalf("authorization header tidak diteruskan")
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	path := filepath.Join(t.TempDir(), "config.yaml")
	cfg := config.Defaults()
	cfg.Auth.BaseURL = server.URL
	if err := config.Save(path, cfg); err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	if err := runLogin(strings.NewReader("1\nak_test_key\n1\n2\n"), &output, path, server.Client()); err != nil {
		t.Fatal(err)
	}
	saved, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(saved), "mode: platform") || !strings.Contains(string(saved), "api_key: ak_test_key") {
		t.Fatal("config login tidak tersimpan")
	}
	if strings.Contains(output.String(), "ak_test_key") {
		t.Fatal("API key tidak boleh tampil di output")
	}
}

func TestRunInitDirectSavesCloudflareCredentials(t *testing.T) {
	t.Parallel()
	path := filepath.Join(t.TempDir(), "config.yaml")
	var output bytes.Buffer
	if err := runInit(strings.NewReader("2\naccount-test\ntoken-test\n"), &output, path); err != nil {
		t.Fatal(err)
	}
	saved, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	contents := string(saved)
	if !strings.Contains(contents, "mode: direct") || !strings.Contains(contents, "account_id: account-test") || !strings.Contains(contents, "api_token: token-test") || !strings.Contains(contents, "primary_model: '@cf/moonshotai/kimi-k2.7-code'") {
		t.Fatal("config init tidak tersimpan")
	}
}

func TestRunLoginOpenAISelectsOpenAIModels(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, request *http.Request) {
		if request.Header.Get("Authorization") != "Bearer sk-test-key" {
			t.Fatal("authorization OpenAI tidak diteruskan")
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()
	original := openAIModelsEndpoint
	openAIModelsEndpoint = server.URL
	t.Cleanup(func() { openAIModelsEndpoint = original })

	path := filepath.Join(t.TempDir(), "config.yaml")
	var output bytes.Buffer
	if err := runLogin(strings.NewReader("3\nsk-test-key\n1\n2\n"), &output, path, server.Client()); err != nil {
		t.Fatal(err)
	}
	saved, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	contents := string(saved)
	if !strings.Contains(contents, "mode: openai") || !strings.Contains(contents, "primary_model: gpt-5.6") || !strings.Contains(contents, "secondary_model: gpt-5.6-mini") {
		t.Fatal("login OpenAI menyimpan model provider yang salah")
	}
}

func TestRunLoginAIStudioUsesGeminiCatalog(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, request *http.Request) {
		if request.URL.Query().Get("key") != "gemini-test-key" {
			t.Fatal("API key AI Studio tidak diteruskan")
		}
		_, _ = w.Write([]byte(`{"models":[{"name":"models/gemini-3.5-flash","supportedGenerationMethods":["generateContent"]},{"name":"models/gemini-3.5-pro","supportedGenerationMethods":["generateContent"]},{"name":"models/embedding-001","supportedGenerationMethods":["embedContent"]}]}`))
	}))
	defer server.Close()
	original := aiStudioModelsEndpoint
	aiStudioModelsEndpoint = server.URL
	t.Cleanup(func() { aiStudioModelsEndpoint = original })

	path := filepath.Join(t.TempDir(), "config.yaml")
	var output bytes.Buffer
	if err := runLogin(strings.NewReader("4\ngemini-test-key\n1\n2\n"), &output, path, server.Client()); err != nil {
		t.Fatal(err)
	}
	saved, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	contents := string(saved)
	if !strings.Contains(contents, "mode: aistudio") || !strings.Contains(contents, "primary_model: gemini-3.5-flash") || !strings.Contains(contents, "secondary_model: gemini-3.5-pro") {
		t.Fatal("login AI Studio menyimpan model provider yang salah")
	}
}

func TestRunLoginCanBeCancelled(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.yaml")
	var output bytes.Buffer
	err := runLogin(strings.NewReader("q\n"), &output, path, http.DefaultClient)
	if !errors.Is(err, errLoginCancelled) {
		t.Fatalf("login cancel harus jelas, mendapat %v", err)
	}
}

func TestRunProofListDoesNotRequireProofID(t *testing.T) {
	t.Parallel()
	var output bytes.Buffer
	if err := runProof(t.TempDir(), []string{"list"}, &output); err != nil {
		t.Fatal(err)
	}
}
