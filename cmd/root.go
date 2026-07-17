package cmd

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"

	"github.com/autokeren/autokeren/ghost"
	"github.com/autokeren/autokeren/internal/config"
	"github.com/autokeren/autokeren/internal/engine"
	"github.com/autokeren/autokeren/internal/workflow"
	"github.com/autokeren/autokeren/ipc"
	"github.com/autokeren/autokeren/ui"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"
)

var (
	projectRoot    string
	configPath     string
	modelOverride  string
	useAIStudio    bool
	useAgy         bool
	planMode       bool
	nonInteractive bool
	engineMode     string
	taskPrompt     string
	resumeSession  string
)

var rootCmd = &cobra.Command{
	Use:   "autokeren [prompt]",
	Short: "autokeren — Cloudflare-first agentic coding CLI",
	Long:  `autokeren adalah CLI agentic coding yang dirancang khusus untuk stack Cloudflare-first.`,
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		prompt := ""
		if len(args) > 0 {
			prompt = args[0]
		}
		if taskPrompt != "" {
			prompt = taskPrompt
		}
		if expanded, handled, err := workflow.Expand(prompt); err != nil {
			fmt.Printf("Error workflow: %v\n", err)
			return
		} else if handled {
			prompt = expanded
		}

		// Tentukan project root default ke direktori kerja saat ini
		if projectRoot == "" {
			var err error
			projectRoot, err = os.Getwd()
			if err != nil {
				projectRoot = "."
			}
		} else {
			absPath, err := filepath.Abs(projectRoot)
			if err == nil {
				projectRoot = absPath
			}
		}

		if (engineMode == "go" || engineMode == "auto") && (prompt != "" || nonInteractive) {
			cfg, err := config.Load(configPath)
			if err != nil {
				fmt.Printf("Error memuat config Go: %v\n", err)
				os.Exit(1)
			}
			if modelOverride != "" {
				cfg.Cloudflare.PrimaryModel = modelOverride
			}
			if planMode {
				cfg.Autokeren.PlanMode = true
			}
			if prompt == "" {
				fmt.Println("[red]Error: Task/Prompt kosong.[/red]")
				os.Exit(1)
			}
			_, err = engine.RunStandalone(context.Background(), cfg, projectRoot, prompt, func(chunk string) { fmt.Print(chunk) }, resumeSession)
			if err == nil {
				fmt.Println()
				return
			}
			if engineMode == "go" {
				fmt.Printf("\nError Go engine: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("\nGo engine gagal (%v), fallback ke Python...\n", err)
		}

		// 1. Inisialisasi IPC Callbacks (Default ke CLI biasa)
		callbacks := &ipc.IPCCallbacks{
			OnModelStart: func() {
				fmt.Print("\n[dim]mikir...[/dim]")
			},
			OnModelEnd: func(content string, modelID string, sessionID string, sessionName string, usage map[string]interface{}) {
				fmt.Println()
			},
			OnChunk: func(text string) {
				fmt.Print(text)
			},
			OnToolStart: func(name string, arguments map[string]interface{}) {
				fmt.Printf("\n  [bold cyan]⏺[/bold cyan] memanggil tool %s...", name)
			},
			OnToolEnd: func(name string, result map[string]interface{}) {
				ok := true
				if val, exists := result["ok"]; exists {
					if b, isBool := val.(bool); isBool {
						ok = b
					}
				}
				if ok {
					fmt.Print(" [green]✓[/green]")
				} else {
					fmt.Printf(" [red]✗ (%v)[/red]", result["error"])
				}
			},
			OnToolOutput: func(name string, line string) {
				fmt.Printf("\n  [dim]│[/dim] %s", line)
			},
			ConfirmPermission: func(name string, desc string, args map[string]interface{}) bool {
				fmt.Printf("\n  [yellow]⚡ %s[/yellow] — %s", name, desc)
				fmt.Print("\n  [yellow]Izinkan? [Y/n]: [/yellow]")

				var input string
				_, err := fmt.Scanln(&input)
				if err != nil || input == "" || input == "y" || input == "Y" {
					return true
				}
				return false
			},
			OnError: func(message string) {
				fmt.Fprintf(os.Stderr, "\n[red]Error: %s[/red]\n", message)
			},
		}

		// 2. Start IPC Client
		client := ipc.NewClient(callbacks)

		// Bangun parameter inisialisasi dinamis dari flag CLI
		opts := make(map[string]interface{})
		if modelOverride != "" {
			opts["model"] = modelOverride
		}
		if useAIStudio {
			opts["aistudio"] = true
		}
		if useAgy {
			opts["agy"] = true
		}
		if planMode {
			opts["plan"] = true
		}
		if resumeSession != "" {
			opts["resume_session"] = resumeSession
		}
		if engineMode == "go" {
			opts["engine"] = "go"
		}

		// 3. Eksekusi Non-Interactive Mode jika ada prompt/task
		if prompt != "" || nonInteractive {
			if prompt == "" {
				fmt.Println("[red]Error: Task/Prompt kosong.[/red]")
				os.Exit(1)
			}

			err := client.Start(projectRoot, configPath, opts)
			if err != nil {
				fmt.Printf("Error: %v\n", err)
				os.Exit(1)
			}
			defer client.Close()

			// Jalankan task
			runParams := map[string]interface{}{
				"user_input": prompt,
			}
			var reply map[string]interface{}
			err = client.Call("agent.run", runParams, &reply)
			if err != nil {
				fmt.Printf("\nError saat eksekusi: %v\n", err)
				os.Exit(1)
			}

			fmt.Println()
			return
		}

		// 4. Jalankan TUI Mode jika dipanggil interaktif (Default)
		ghostMgr := ghost.NewGhostManager(projectRoot)
		m := ui.NewMainModel(client, ghostMgr, projectRoot, configPath, opts)
		p := tea.NewProgram(m, tea.WithAltScreen())

		// Arahkan callbacks agar menyalurkan pesan ke Bubble Tea program
		callbacks.OnModelStart = func() { p.Send(ui.ModelStartMsg{}) }
		callbacks.OnModelEnd = func(content string, modelID string, sessionID string, sessionName string, usage map[string]interface{}) {
			p.Send(ui.ModelEndMsg{Content: content, ModelID: modelID, SessionID: sessionID, SessionName: sessionName, Usage: usage})
		}
		callbacks.OnChunk = func(text string) { p.Send(ui.ChunkMsg{Text: text}) }
		callbacks.OnToolStart = func(name string, arguments map[string]interface{}) {
			p.Send(ui.ToolStartMsg{Name: name, Args: arguments})
		}
		callbacks.OnToolEnd = func(name string, result map[string]interface{}) {
			p.Send(ui.ToolEndMsg{Name: name, Result: result})
		}
		callbacks.OnToolOutput = func(name string, line string) {
			p.Send(ui.ToolOutputMsg{Name: name, Line: line})
		}
		callbacks.OnRetry = func(attempt int, delay float64, message string) {
			p.Send(ui.RetryMsg{Attempt: attempt, Delay: delay, Message: message})
		}
		callbacks.OnSessionSaved = func(sessionID string, sessionName string) {
			p.Send(ui.SessionSavedMsg{SessionID: sessionID, SessionName: sessionName})
		}
		callbacks.ConfirmPermission = func(name string, desc string, args map[string]interface{}) bool {
			ch := make(chan bool)
			p.Send(ui.PermissionConfirmReq{Name: name, Description: desc, Arguments: args, RespChan: ch})
			return <-ch
		}
		callbacks.OnError = func(message string) { p.Send(ui.ErrorMsg{Message: message}) }

		if _, err := p.Run(); err != nil {
			fmt.Printf("Terjadi error di TUI: %v\n", err)
			os.Exit(1)
		}
		return
	},
}

func runInteractiveLoop(client *ipc.Client) {
	fmt.Println("Ketik perintah Anda (atau /q untuk keluar):")
	scanner := bufio.NewScanner(os.Stdin)

	for {
		fmt.Print("\nkamu> ")
		if !scanner.Scan() {
			break
		}
		text := scanner.Text()
		if text == "" {
			continue
		}
		if text == "/q" || text == "/quit" {
			fmt.Println("Sampai jumpa!")
			break
		}

		runParams := map[string]interface{}{
			"user_input": text,
		}
		var reply map[string]interface{}
		err := client.Call("agent.run", runParams, &reply)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
		}
		fmt.Println()
	}
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.Flags().StringVarP(&projectRoot, "project-root", "w", "", "Path ke project root")
	rootCmd.Flags().StringVar(&configPath, "config", "", "Path ke custom config YAML")
	rootCmd.Flags().StringVarP(&modelOverride, "model", "m", "", "Override model primary")
	rootCmd.Flags().BoolVar(&useAIStudio, "aistudio", false, "Gunakan backend Google AI Studio")
	rootCmd.Flags().BoolVar(&useAgy, "agy", false, "Gunakan backend Google Antigravity")
	rootCmd.Flags().BoolVar(&planMode, "plan", false, "Mulai dalam plan mode")
	rootCmd.Flags().BoolVar(&nonInteractive, "non-interactive", false, "Jalankan single task tanpa REPL")
	rootCmd.Flags().StringVar(&engineMode, "engine", "go", "Engine runtime: go (default), auto, atau python")
	rootCmd.Flags().StringVar(&taskPrompt, "task", "", "Deskripsi task untuk dijalankan")
	rootCmd.Flags().StringVarP(&resumeSession, "resume", "r", "", "Resume sesi percakapan dari disk")
}
