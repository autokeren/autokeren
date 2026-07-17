package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"github.com/autokeren/autokeren/internal/tool"
	"io"
	"os"
	"os/exec"
	"sync"
	"time"
)

type Server struct {
	Name    string
	Command []string
	Env     map[string]string
	proc    *exec.Cmd
	stdin   io.WriteCloser
	lines   chan []byte
	mu      sync.Mutex
	nextID  int
}

func NewServer(name string, command []string, env map[string]string) *Server {
	return &Server{Name: name, Command: command, Env: env, nextID: 1}
}
func (s *Server) Start(ctx context.Context) error {
	if len(s.Command) == 0 {
		return fmt.Errorf("MCP %s command is empty", s.Name)
	}
	s.proc = exec.CommandContext(ctx, s.Command[0], s.Command[1:]...)
	s.proc.Env = os.Environ()
	for k, v := range s.Env {
		s.proc.Env = append(s.proc.Env, k+"="+v)
	}
	stdin, err := s.proc.StdinPipe()
	if err != nil {
		return err
	}
	stdout, err := s.proc.StdoutPipe()
	if err != nil {
		return err
	}
	s.stdin = stdin
	s.lines = make(chan []byte, 32)
	go func() {
		defer close(s.lines)
		scanner := bufio.NewScanner(stdout)
		for scanner.Scan() {
			s.lines <- append([]byte(nil), scanner.Bytes()...)
		}
	}()
	if err := s.proc.Start(); err != nil {
		return err
	}
	if _, err := s.request(ctx, "initialize", map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}}, "clientInfo": map[string]any{"name": "autokeren-go", "version": "0.11"}}); err != nil {
		return err
	}
	return s.notify("notifications/initialized", nil)
}
func (s *Server) Close() error {
	if s.proc == nil || s.proc.Process == nil {
		return nil
	}
	_ = s.proc.Process.Kill()
	return s.proc.Wait()
}
func (s *Server) request(ctx context.Context, method string, params any) (map[string]any, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	id := s.nextID
	s.nextID++
	payload := map[string]any{"jsonrpc": "2.0", "id": id, "method": method}
	if params != nil {
		payload["params"] = params
	}
	raw, _ := json.Marshal(payload)
	if _, err := s.stdin.Write(append(raw, '\n')); err != nil {
		return nil, err
	}
	timer := time.NewTimer(30 * time.Second)
	defer timer.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-timer.C:
			return nil, fmt.Errorf("MCP %s timeout", s.Name)
		case line, ok := <-s.lines:
			if !ok {
				return nil, fmt.Errorf("MCP %s stopped", s.Name)
			}
			var resp map[string]any
			if json.Unmarshal(line, &resp) != nil {
				continue
			}
			if fmt.Sprint(resp["id"]) != fmt.Sprint(id) {
				continue
			}
			if e, ok := resp["error"]; ok {
				return nil, fmt.Errorf("MCP error: %v", e)
			}
			result, _ := resp["result"].(map[string]any)
			return result, nil
		}
	}
}
func (s *Server) notify(method string, params any) error {
	payload := map[string]any{"jsonrpc": "2.0", "method": method}
	if params != nil {
		payload["params"] = params
	}
	raw, _ := json.Marshal(payload)
	_, err := s.stdin.Write(append(raw, '\n'))
	return err
}
func (s *Server) Tools(ctx context.Context) ([]tool.Tool, error) {
	result, err := s.request(ctx, "tools/list", nil)
	if err != nil {
		return nil, err
	}
	raw, _ := json.Marshal(result["tools"])
	var specs []struct {
		Name, Description string
		InputSchema       map[string]any `json:"inputSchema"`
	}
	if json.Unmarshal(raw, &specs) != nil {
		return nil, fmt.Errorf("invalid MCP tools response")
	}
	out := make([]tool.Tool, 0, len(specs))
	for _, spec := range specs {
		out = append(out, remoteTool{server: s, name: spec.Name, description: spec.Description, schema: spec.InputSchema})
	}
	return out, nil
}

type remoteTool struct {
	server            *Server
	name, description string
	schema            map[string]any
}

func (t remoteTool) Definition() tool.Definition {
	return tool.Definition{Name: t.name, Description: t.description, Parameters: t.schema}
}
func (t remoteTool) NeedsPermission(map[string]any) (bool, string) {
	return true, "MCP tool: " + t.name
}
func (t remoteTool) Run(ctx context.Context, args map[string]any, _ tool.Emitter) tool.Result {
	result, err := t.server.request(ctx, "tools/call", map[string]any{"name": t.name, "arguments": args})
	if err != nil {
		return tool.Result{OK: false, Error: err.Error()}
	}
	if failed, ok := result["isError"].(bool); ok && failed {
		return tool.Result{OK: false, Error: fmt.Sprint(result["content"])}
	}
	return tool.Result{OK: true, Output: result["content"]}
}
