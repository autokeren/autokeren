package engine

import (
	"context"
	"fmt"
	"github.com/autokeren/autokeren/internal/model"
	"github.com/autokeren/autokeren/internal/provider"
)

type Runner struct{ Provider provider.Provider }

func (r Runner) RunTurn(ctx context.Context, request model.Request, onChunk provider.ChunkHandler) (model.Response, error) {
	if r.Provider == nil {
		return model.Response{}, fmt.Errorf("agent provider is nil")
	}
	return r.Provider.Complete(ctx, request, onChunk)
}
