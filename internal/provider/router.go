package provider

import (
	"context"
	"errors"
	"fmt"
	"math/rand/v2"
	"strings"
	"sync"
	"time"

	"github.com/autokeren/autokeren/internal/model"
	"github.com/sony/gobreaker/v2"
)

type RetryPolicy struct {
	MaxRetries      int
	BaseDelay       time.Duration
	MaxDelay        time.Duration
	ExponentialBase float64
	Jitter          bool
}

type Target struct {
	ModelID  string
	Provider Provider
}

type RetryEvent struct {
	Attempt int
	Delay   time.Duration
	Message string
}

type RouterConfig struct {
	Targets                 []Target
	Retry                   RetryPolicy
	CircuitFailureThreshold int
	CircuitOpenDuration     time.Duration
	State                   *RouterState
	OnRetry                 func(RetryEvent)
}

type CircuitStatus struct {
	State               string `json:"state"`
	Requests            uint32 `json:"requests"`
	TotalSuccesses      uint32 `json:"total_successes"`
	TotalFailures       uint32 `json:"total_failures"`
	ConsecutiveFailures uint32 `json:"consecutive_failures"`
}

type RouterState struct {
	mu       sync.Mutex
	breakers map[string]*gobreaker.CircuitBreaker[model.Response]
}

func NewRouterState() *RouterState {
	return &RouterState{breakers: make(map[string]*gobreaker.CircuitBreaker[model.Response])}
}

func (s *RouterState) breaker(modelID string, threshold int, openDuration time.Duration) *gobreaker.CircuitBreaker[model.Response] {
	if threshold <= 0 {
		threshold = 5
	}
	if openDuration <= 0 {
		openDuration = 30 * time.Second
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if breaker, ok := s.breakers[modelID]; ok {
		return breaker
	}
	breaker := gobreaker.NewCircuitBreaker[model.Response](gobreaker.Settings{
		Name:    modelID,
		Timeout: openDuration,
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			return int(counts.ConsecutiveFailures) >= threshold
		},
		IsExcluded: func(err error) bool {
			return errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) || IsContextLimit(err)
		},
	})
	s.breakers[modelID] = breaker
	return breaker
}

func (s *RouterState) Status() map[string]CircuitStatus {
	if s == nil {
		return map[string]CircuitStatus{}
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	status := make(map[string]CircuitStatus, len(s.breakers))
	for modelID, breaker := range s.breakers {
		counts := breaker.Counts()
		status[modelID] = CircuitStatus{
			State:               circuitStateName(breaker.State()),
			Requests:            counts.Requests,
			TotalSuccesses:      counts.TotalSuccesses,
			TotalFailures:       counts.TotalFailures,
			ConsecutiveFailures: counts.ConsecutiveFailures,
		}
	}
	return status
}

func circuitStateName(state gobreaker.State) string {
	switch state {
	case gobreaker.StateOpen:
		return "open"
	case gobreaker.StateHalfOpen:
		return "half_open"
	default:
		return "closed"
	}
}

type Router struct {
	targets             []Target
	retry               RetryPolicy
	state               *RouterState
	circuitThreshold    int
	circuitOpenDuration time.Duration
	onRetry             func(RetryEvent)
	sleep               func(context.Context, time.Duration) error
	random              func() float64
}

func NewRouter(cfg RouterConfig) (*Router, error) {
	if len(cfg.Targets) == 0 {
		return nil, errors.New("router requires at least one model target")
	}
	targets := make([]Target, 0, len(cfg.Targets))
	seen := make(map[string]struct{}, len(cfg.Targets))
	for _, target := range cfg.Targets {
		if strings.TrimSpace(target.ModelID) == "" {
			return nil, errors.New("router model id is empty")
		}
		if target.Provider == nil {
			return nil, fmt.Errorf("router provider for %s is nil", target.ModelID)
		}
		if _, exists := seen[target.ModelID]; exists {
			continue
		}
		seen[target.ModelID] = struct{}{}
		targets = append(targets, target)
	}
	if len(targets) == 0 {
		return nil, errors.New("router requires a usable model target")
	}
	if cfg.Retry.MaxRetries < 0 {
		cfg.Retry.MaxRetries = 0
	}
	if cfg.Retry.ExponentialBase <= 0 {
		cfg.Retry.ExponentialBase = 2
	}
	if cfg.State == nil {
		cfg.State = NewRouterState()
	}
	return &Router{
		targets:             targets,
		retry:               cfg.Retry,
		state:               cfg.State,
		circuitThreshold:    cfg.CircuitFailureThreshold,
		circuitOpenDuration: cfg.CircuitOpenDuration,
		onRetry:             cfg.OnRetry,
		sleep:               sleepWithContext,
		random:              rand.Float64,
	}, nil
}

func (r *Router) Complete(ctx context.Context, request model.Request, onChunk ChunkHandler) (model.Response, error) {
	if r == nil || len(r.targets) == 0 {
		return model.Response{}, errors.New("router has no model targets")
	}
	var lastErr error
	for index, target := range r.targets {
		breaker := r.state.breaker(target.ModelID, r.circuitThreshold, r.circuitOpenDuration)
		response, err := breaker.Execute(func() (model.Response, error) {
			return r.completeTarget(ctx, target, request, onChunk)
		})
		if err == nil {
			response.Model = target.ModelID
			return response, nil
		}
		lastErr = err
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) || IsContextLimit(err) || StreamStarted(err) {
			return model.Response{}, err
		}
		if index < len(r.targets)-1 {
			next := r.targets[index+1].ModelID
			if errors.Is(err, gobreaker.ErrOpenState) || errors.Is(err, gobreaker.ErrTooManyRequests) {
				r.emit(RetryEvent{Message: fmt.Sprintf("circuit %s sedang terbuka; fallback ke %s", target.ModelID, next)})
			} else {
				r.emit(RetryEvent{Message: fmt.Sprintf("model %s gagal; fallback ke %s", target.ModelID, next)})
			}
		}
	}
	return model.Response{}, lastErr
}

func (r *Router) completeTarget(ctx context.Context, target Target, request model.Request, onChunk ChunkHandler) (model.Response, error) {
	request.Model = target.ModelID
	for attempt := 0; ; attempt++ {
		streamStarted := false
		wrappedChunk := func(chunk string) error {
			streamStarted = true
			if onChunk == nil {
				return nil
			}
			return onChunk(chunk)
		}
		response, err := target.Provider.Complete(ctx, request, wrappedChunk)
		if err == nil {
			return response, nil
		}
		if streamStarted && !StreamStarted(err) {
			err = &Error{StreamStarted: true, Cause: err}
		}
		if !r.shouldRetry(err, attempt) {
			return model.Response{}, err
		}
		delay := r.backoff(attempt, err)
		r.emit(RetryEvent{Attempt: attempt + 1, Delay: delay, Message: fmt.Sprintf("model %s gagal: %v", target.ModelID, err)})
		if err := r.sleep(ctx, delay); err != nil {
			return model.Response{}, err
		}
	}
}

func (r *Router) shouldRetry(err error, attempt int) bool {
	if attempt >= r.retry.MaxRetries || err == nil || StreamStarted(err) || IsContextLimit(err) {
		return false
	}
	if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
		return false
	}
	providerErr, ok := AsError(err)
	if !ok {
		return false
	}
	if providerErr.Status == 0 {
		return true
	}
	switch providerErr.Status {
	case httpStatusRequestTimeout, httpStatusTooManyRequests, 500, 502, 503, 504:
		return true
	default:
		return false
	}
}

func IsContextLimit(err error) bool {
	if err == nil {
		return false
	}
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "8007") || strings.Contains(message, "context length") || strings.Contains(message, "context window") || strings.Contains(message, "context limit") || strings.Contains(message, "exceeds")
}

const (
	httpStatusRequestTimeout  = 408
	httpStatusTooManyRequests = 429
)

func (r *Router) backoff(attempt int, err error) time.Duration {
	if providerErr, ok := AsError(err); ok && providerErr.RetryAfter > 0 {
		return r.capDelay(providerErr.RetryAfter)
	}
	if r.retry.BaseDelay <= 0 {
		return 0
	}
	delay := float64(r.retry.BaseDelay) * pow(r.retry.ExponentialBase, attempt)
	if r.retry.Jitter {
		delay *= 0.5 + r.random()*0.5
	}
	return r.capDelay(time.Duration(delay))
}

func (r *Router) capDelay(delay time.Duration) time.Duration {
	if r.retry.MaxDelay > 0 && delay > r.retry.MaxDelay {
		return r.retry.MaxDelay
	}
	return delay
}

func (r *Router) emit(event RetryEvent) {
	if r.onRetry != nil {
		r.onRetry(event)
	}
}

func sleepWithContext(ctx context.Context, delay time.Duration) error {
	if delay <= 0 {
		return ctx.Err()
	}
	timer := time.NewTimer(delay)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

func pow(base float64, exponent int) float64 {
	result := 1.0
	for index := 0; index < exponent; index++ {
		result *= base
	}
	return result
}
