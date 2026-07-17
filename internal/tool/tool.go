package tool

import "context"

type Result struct {
	OK     bool   `json:"ok"`
	Output any    `json:"output,omitempty"`
	Error  string `json:"error,omitempty"`
}

type Definition struct {
	Name               string         `json:"name"`
	Description        string         `json:"description"`
	Parameters         map[string]any `json:"parameters"`
	RequiresPermission bool           `json:"requires_permission"`
}

type Emitter func(string)

type Tool interface {
	Definition() Definition
	NeedsPermission(args map[string]any) (bool, string)
	Run(ctx context.Context, args map[string]any, emit Emitter) Result
}

type Registry struct{ tools map[string]Tool }

func NewRegistry() *Registry                     { return &Registry{tools: make(map[string]Tool)} }
func (r *Registry) Register(t Tool) *Registry    { r.tools[t.Definition().Name] = t; return r }
func (r *Registry) Get(name string) (Tool, bool) { t, ok := r.tools[name]; return t, ok }
func (r *Registry) Definitions() []Definition {
	definitions := make([]Definition, 0, len(r.tools))
	for _, t := range r.tools {
		definitions = append(definitions, t.Definition())
	}
	return definitions
}
func (r *Registry) Run(ctx context.Context, name string, args map[string]any, emit Emitter) Result {
	t, ok := r.Get(name)
	if !ok {
		return Result{OK: false, Error: "tool not found: " + name}
	}
	return t.Run(ctx, args, emit)
}
