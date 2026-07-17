package engine

import (
	"context"
	"fmt"
	"github.com/autokeren/autokeren/internal/config"
	contextstore "github.com/autokeren/autokeren/internal/context"
	"github.com/autokeren/autokeren/internal/mcp"
	"github.com/autokeren/autokeren/internal/provider"
	"github.com/autokeren/autokeren/internal/tool"
	"net/url"
	"strings"
)

func RunStandalone(ctx context.Context, cfg config.Config, root, prompt string, onChunk func(string)) (string, error) {
	endpoint := cfg.Auth.BaseURL
	if endpoint == "" {
		return "", fmt.Errorf("auth base_url is empty")
	}
	endpoint = strings.TrimRight(endpoint, "/")
	if parsed, err := url.Parse(endpoint); err == nil && parsed.Path == "" {
		endpoint += "/v1/chat/completions"
	}
	registry := tool.NewRegistry().Register(tool.ReadFile{Root: root}).Register(tool.ListFiles{Root: root}).Register(tool.Shell{Root: root})
	var mcpServers []*mcp.Server
	for _, spec := range cfg.MCPServers {
		if !spec.Enabled {
			continue
		}
		server := mcp.NewServer(spec.Name, spec.Command, spec.Env)
		if err := server.Start(ctx); err != nil {
			return "", err
		}
		mcpServers = append(mcpServers, server)
		defer server.Close()
		remoteTools, err := server.Tools(ctx)
		if err != nil {
			return "", err
		}
		for _, remote := range remoteTools {
			registry.Register(remote)
		}
	}
	loop := &Loop{Runner: Runner{Provider: provider.OpenAICompatible{Endpoint: endpoint, APIKey: cfg.Auth.APIKey}}, Model: cfg.Cloudflare.PrimaryModel, Temperature: cfg.Cloudflare.Temperature, MaxTokens: cfg.Cloudflare.MaxTokens, Tools: registry, Context: contextstore.New(cfg.Autokeren.ContextWindow, cfg.Autokeren.AutoCompact, cfg.Autokeren.AutoCompactThreshold), MaxIterations: cfg.Autokeren.MaxIterations}
	response, err := loop.Run(ctx, prompt, Events{OnChunk: onChunk, ConfirmPermission: func(name string, _ string, _ map[string]any) bool { return name != "run_shell" }})
	if err != nil {
		return "", err
	}
	return response.Content, nil
}
