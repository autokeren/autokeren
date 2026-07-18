package engine

import (
	"context"
	"fmt"
	"github.com/autokeren/autokeren/ghost"
	"github.com/autokeren/autokeren/internal/browser"
	"github.com/autokeren/autokeren/internal/config"
	contextstore "github.com/autokeren/autokeren/internal/context"
	"github.com/autokeren/autokeren/internal/director"
	"github.com/autokeren/autokeren/internal/mcp"
	"github.com/autokeren/autokeren/internal/memory"
	"github.com/autokeren/autokeren/internal/model"
	promptbuilder "github.com/autokeren/autokeren/internal/prompt"
	"github.com/autokeren/autokeren/internal/provider"
	"github.com/autokeren/autokeren/internal/session"
	"github.com/autokeren/autokeren/internal/tool"
	"github.com/autokeren/autokeren/internal/workflow"
	"net/http"
	"os"
	"sort"
	"strings"
	"time"
)

var sharedBrowser = browser.GetBrowserManager()

const fallbackSystemPrompt = "Kamu adalah Autokeren, asisten coding CLI berbahasa Indonesia. Jangan mengaku sebagai Claude, ChatGPT, atau produk lain. Jika ditanya siapa kamu, jawab bahwa kamu adalah Autokeren. Bantu pengguna secara praktis dan jujur."

func defaultPermission(name string, _ string, _ map[string]any) bool {
	if os.Getenv("AUTOKEREN_GHOST_CHILD") != "1" {
		return name != "run_shell"
	}
	for _, allowed := range strings.Split(os.Getenv("AUTOKEREN_GHOST_ALLOWED_TOOLS"), ",") {
		if strings.TrimSpace(allowed) == name {
			return true
		}
	}
	return false
}

func RunStandalone(ctx context.Context, cfg config.Config, root, prompt string, onChunk func(string), resume string) (string, error) {
	return RunStandaloneEvents(ctx, cfg, root, prompt, Events{OnChunk: onChunk}, resume)
}

func RunStandaloneEvents(ctx context.Context, cfg config.Config, root, prompt string, events Events, resume string) (string, error) {
	return RunStandaloneEventsWithRouterState(ctx, cfg, root, prompt, events, resume, nil)
}

func RunStandaloneEventsWithRouterState(ctx context.Context, cfg config.Config, root, prompt string, events Events, resume string, routerState *provider.RouterState) (string, error) {
	verification := workflow.NewVerification(prompt)
	if verification != nil {
		onToolStart := events.OnToolStart
		events.OnToolStart = func(name string, args map[string]any) {
			verification.ObserveStart(name, args)
			if onToolStart != nil {
				onToolStart(name, args)
			}
		}
		onToolEnd := events.OnToolEnd
		events.OnToolEnd = func(name string, result tool.Result) {
			verification.ObserveEnd(name, result)
			if onToolEnd != nil {
				onToolEnd(name, result)
			}
		}
	}
	ghostManager := ghost.NewGhostManager(root)
	coordinator := director.New(root, ghostManager)
	registry := tool.NewRegistry().Register(tool.ReadFile{Root: root}).Register(tool.WriteFile{Root: root}).Register(tool.PatchFile{Root: root}).Register(tool.ListFiles{Root: root}).Register(tool.SearchCode{Root: root}).Register(tool.GitStatus{Root: root}).Register(tool.GitDiff{Root: root}).Register(tool.GitLog{Root: root}).Register(tool.GitCommit{Root: root}).Register(tool.GitBranch{Root: root}).Register(tool.GitAutoCommit{Root: root}).Register(tool.NewTodoList(root)).Register(tool.NewKanban(root)).Register(tool.Proof{Root: root}).Register(tool.Remember{Root: root}).Register(tool.FetchURL{}).Register(tool.CFDeploy{Root: root}).Register(tool.CFBuild{Root: root}).Register(tool.CFVerify{Root: root, Browser: sharedBrowser}).Register(tool.FDDM{}).Register(tool.Genome{Root: root}).Register(tool.CreateProject{Config: cfg}).Register(tool.DeployProject{Config: cfg, Root: root}).Register(tool.ListProjects{Config: cfg}).Register(tool.RepoMap{Root: root}).Register(tool.CFKV{Config: cfg}).Register(tool.CFD1{Config: cfg}).Register(tool.Browser{Manager: sharedBrowser}).Register(tool.Research{}).Register(tool.Review{Root: root}).Register(tool.SecurityScan{Root: root}).Register(tool.Rewind{Root: root}).Register(tool.SpawnGhost{Manager: ghostManager}).Register(tool.AwaitAgents{Coordinator: coordinator}).Register(tool.Collaborate{Manager: ghostManager}).Register(tool.CheckGhost{Manager: ghostManager}).Register(tool.StopGhost{Manager: ghostManager}).Register(tool.Shell{Root: root})
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
	timeout := time.Duration(cfg.Cloudflare.Timeout * float64(time.Second))
	if timeout <= 0 {
		timeout = 120 * time.Second
	}
	store := contextstore.New(cfg.Autokeren.ContextWindow, cfg.Autokeren.AutoCompact, cfg.Autokeren.AutoCompactThreshold)
	store.SetCompactTail(cfg.Autokeren.CompactTailTurns)
	sessions, err := session.NewManager(root)
	if err != nil {
		return "", err
	}
	sessionID := ""
	sessionName := ""
	if resume != "" && resume != "default" {
		data, loadErr := sessions.Load(resume)
		if loadErr != nil {
			return "", fmt.Errorf("load session %s: %w", resume, loadErr)
		}
		sessionID = data.ID
		sessionName = data.Name
		store.Replace(data.Messages)
	}
	memoryStore := memory.New(root)
	systemPrompt := promptbuilder.Build(promptbuilder.Options{
		ProjectRoot:  root,
		ToolNames:    registryToolNames(registry),
		PlanMode:     cfg.Autokeren.PlanMode,
		MaxToolCalls: cfg.Autokeren.MaxToolCalls,
		Language:     cfg.Autokeren.Language,
	})
	store.Replace(withSystemPrompt(store.Messages(), systemPrompt))
	prelude := []model.Message{}
	if cfg.Autokeren.MemoryEnabled {
		if context := memoryStore.Context(prompt, 3); context != "" {
			prelude = append(prelude, model.Message{Role: "system", Content: context})
		}
	}
	targets, err := provider.TargetsForConfig(cfg, &http.Client{Timeout: timeout})
	if err != nil {
		return "", err
	}
	primaryModel := targets[0].ModelID
	router, err := provider.NewRouter(provider.RouterConfig{
		Targets: targets,
		Retry: provider.RetryPolicy{
			MaxRetries:      cfg.Retry.MaxRetries,
			BaseDelay:       time.Duration(cfg.Retry.BaseDelay * float64(time.Second)),
			MaxDelay:        time.Duration(cfg.Retry.MaxDelay * float64(time.Second)),
			ExponentialBase: cfg.Retry.ExponentialBase,
			Jitter:          cfg.Retry.Jitter,
		},
		CircuitFailureThreshold: cfg.Retry.CircuitFailureThreshold,
		CircuitOpenDuration:     time.Duration(cfg.Retry.CircuitOpenSeconds) * time.Second,
		State:                   routerState,
		OnRetry: func(event provider.RetryEvent) {
			if events.OnRetry != nil {
				events.OnRetry(event.Attempt, event.Delay, event.Message)
			}
		},
	})
	if err != nil {
		return "", err
	}
	loop := &Loop{Runner: Runner{Provider: router}, Model: primaryModel, Temperature: cfg.Cloudflare.Temperature, MaxTokens: cfg.Cloudflare.MaxTokens, Tools: registry, Context: store, RequestPrelude: prelude, MaxIterations: cfg.Autokeren.MaxIterations, PlanMode: cfg.Autokeren.PlanMode}
	if events.ConfirmPermission == nil {
		events.ConfirmPermission = defaultPermission
	}
	response, err := loop.Run(ctx, prompt, events)
	if err != nil {
		return "", err
	}
	if report := verification.Report(); report != "" {
		response.Content = strings.TrimSpace(response.Content + "\n\n" + report)
		messages := store.Messages()
		for index := len(messages) - 1; index >= 0; index-- {
			if messages[index].Role == "assistant" {
				messages[index].Content = response.Content
				store.Replace(messages)
				break
			}
		}
	}
	if events.OnResponse != nil {
		events.OnResponse(response)
	}
	if cfg.Autokeren.AutoSaveSession {
		if sessionName == "" {
			sessionName = automaticSessionName(prompt)
		}
		saved, saveErr := sessions.Save(sessionName, store.Messages(), response.Usage, sessionID)
		if saveErr != nil {
			return "", fmt.Errorf("auto-save session: %w", saveErr)
		}
		if events.OnSessionSaved != nil {
			events.OnSessionSaved(saved.ID, saved.Name)
		}
	}
	return response.Content, nil
}

func automaticSessionName(input string) string {
	words := strings.FieldsFunc(strings.ToLower(input), func(r rune) bool {
		return !(r >= 'a' && r <= 'z') && !(r >= '0' && r <= '9')
	})
	if len(words) > 3 {
		words = words[:3]
	}
	slug := strings.Join(words, "-")
	if slug == "" {
		slug = "session"
	}
	return time.Now().Format("20060102-150405") + "-" + slug
}

func withCurrentSystemPrompt(messages []model.Message) []model.Message {
	return withSystemPrompt(messages, fallbackSystemPrompt)
}

func withSystemPrompt(messages []model.Message, systemPrompt string) []model.Message {
	if strings.TrimSpace(systemPrompt) == "" {
		systemPrompt = fallbackSystemPrompt
	}
	if len(messages) == 0 || messages[0].Role != "system" {
		return append([]model.Message{{Role: "system", Content: systemPrompt}}, messages...)
	}
	updated := append([]model.Message(nil), messages...)
	updated[0].Content = systemPrompt
	return updated
}

func registryToolNames(registry *tool.Registry) []string {
	definitions := registry.Definitions()
	names := make([]string, 0, len(definitions))
	for _, definition := range definitions {
		names = append(names, definition.Name)
	}
	sort.Strings(names)
	return names
}
