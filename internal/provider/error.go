package provider

import (
	"errors"
	"fmt"
	"time"
)

type Error struct {
	Status        int
	RetryAfter    time.Duration
	StreamStarted bool
	Cause         error
}

func (e *Error) Error() string {
	if e == nil {
		return "provider error"
	}
	if e.Cause == nil {
		if e.Status > 0 {
			return fmt.Sprintf("provider status %d", e.Status)
		}
		return "provider error"
	}
	return e.Cause.Error()
}

func (e *Error) Unwrap() error {
	if e == nil {
		return nil
	}
	return e.Cause
}

func AsError(err error) (*Error, bool) {
	var providerErr *Error
	if errors.As(err, &providerErr) {
		return providerErr, true
	}
	return nil, false
}

func StreamStarted(err error) bool {
	providerErr, ok := AsError(err)
	return ok && providerErr.StreamStarted
}
