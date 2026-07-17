#!/usr/bin/env bash
set -euo pipefail

: "${AUTOKEREN_API_KEY:?Set AUTOKEREN_API_KEY first}"
export AUTOKEREN_API_KEY

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
go run . --engine go --non-interactive --task "Reply with exactly: AUTOKEREN_GO_E2E_OK" "$@"
