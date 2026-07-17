package provider

import (
	"context"
	"github.com/autokeren/autokeren/internal/model"
)

type ChunkHandler func(string) error

type Provider interface {
	Complete(ctx context.Context, request model.Request, onChunk ChunkHandler) (model.Response, error)
}
