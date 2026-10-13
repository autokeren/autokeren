# Change Coordination Layer — Design (MVP)

Our entry for the Cloudflare "Build the next GitHub" challenge. A coordination layer so that many
AI agents can work in parallel on the same changes without silent collisions (last-write-wins).

## Problem

autokeren can already spawn many parallel ghost agents (`spawn_agent`, the `internal/project`
worker DAG), but there is no coordination primitive: two agents editing the same file will
silently overwrite each other. Git detects conflicts too late (at merge time, after the work is
already wasted). This layer detects the POTENTIAL conflict before the edit happens.

## Core Concepts

| Concept | Definition |
|---|---|
| **Claim / Lease** | An exclusive edit right over one path, owned by an `agent_id`, with a TTL, auto-expiry, and explicit release. Multi-path claims are atomic (all-or-nothing). |
| **Conflict** | A claim on a path still held by another agent → structured response: owner, remaining TTL (seconds), queue depth ahead, and the `wait=false` (fail fast) / `wait=true` (join the FIFO) option. |
| **Merge queue** | A per-branch FIFO queue of changes (set-of-paths). Each change is path-overlap tested against every change ahead of it. |
| **Event log** | Append-only audit: every grant/conflict/queue/promotion/release/expiry is recorded with a timestamp. |

Merge queue statuses:
- `pass` — nothing ahead of it (head) → cleared to merge now.
- `queued` — something is ahead, NO overlap → safe, waiting its turn (FIFO discipline).
- `conflict` — path overlap with ≥1 change ahead → must wait for that change to finish.

Every `dequeue` re-evaluates the status of all changes behind it.

## API (identical for local mode and production)

```
claim(paths, agent_id, ttl_seconds, branch?, wait) -> {granted | conflict | queued}
release(agent_id, paths?, request_id?, cancel_waiters?) -> {released, cancelled, promoted}
status(path?, agent_id?) -> {claims, waiters, queues}
queue_enqueue(branch, paths, agent_id, change_id?) -> {change_id, position, status, blocked_by}
queue_status(branch?, change_id?) -> listing + status
queue_dequeue(branch, change_id) -> removed + re-evaluation
events(limit?) -> audit trail
```

## Architecture — two backends, one contract

### Local mode (this MVP, runnable by judges without deploying anything)

- State is stored in `<root>/.autokeren/coord.json` — a single JSON file, written atomically
  (tmp + rename, 0600), following the repo's persistence pattern (`.autokeren/*.json`).
- **The file is the single source of truth**: every operation (1) acquires `flock` on
  `coord.json.lock`, (2) reloads state from disk, (3) mutates, (4) writes atomically, (5) drops
  the lock. As a result, ghost agents — separate OS processes — still coordinate through the
  file; there is no shared memory at all. (Windows fallback: in-process threading.Lock only;
  limitation recorded, demo targets Linux/macOS.)
- **Lazy TTL sweep** at the start of every operation: expired leases are removed
  (`lease_expired` event), then FIFO waiters are promoted when ALL of their requested paths are
  free.
- A multi-path waiter is only promoted once its entire path set is free (prevents deadlocks
  between multi-path claims).
- The event log is capped at the last 2000 entries to keep the file small.

### Production target: Cloudflare Worker + Durable Objects + D1

- **Worker** — an HTTP API with exactly the same surface as the local API above; auth follows the
  existing gateway API-key pattern (`autokeren-dev-api`).
- **Durable Objects**:
  - `ClaimShardDO` (one per project): the claim map + wait queue. A single-writer DO means
    claim/release is race-free without explicit transactions; it replaces the local `flock`.
  - `BranchQueueDO` (one per branch): serializes enqueue/dequeue + status re-evaluation.
  - **DO alarms** replace the lazy sweep: one alarm per lease → push-based auto-expiry,
  no polling, no cron.
- **D1** — append-only event log + queue history (per-project audit/analytics), config.
- **Why DO + D1, not KV/R2**: claim coordination needs linearizability — KV is only eventually
  consistent (two agents could both "win" a lease). DOs provide a single writer plus built-in
  alarms; D1 provides cheap relational history with zero ops. R2 is only for large artifacts.
  The `ClaimShardDO`/`BranchQueueDO` design is a direct lift of the `CoordStore` methods (same
  state shape, same algorithms, only a different medium).

## Runtime decision (trade-off recorded, not blocking)

**The MVP is implemented in the Python compat layer** (`autokeren/coord/`), not Go-native:

1. The demo MUST run via `python3 examples/coord-demo/demo.py` without API keys or dependencies —
   a stdlib-only core makes that possible.
2. Speed toward the deadline (Oct 14): one runtime beats two parallel runtimes.
3. The tools register in the Python registry per AGENTS.md (`autokeren/tools/__init__.py`).

Accepted consequence: the default Go engine does not yet expose `claim_files` etc. Go parity is a
mechanical follow-up — the `internal/tool` contract (struct + `Definition()` +
`NeedsPermission()` + `Run()`, registration at `internal/engine/standalone.go:102`) and the store
semantics are already fixed in this document; the port is ≈300 lines of Go. The local API surface
== the Worker HTTP API, so swapping the backend never changes the tools.

## CLI Tools (Python compat, tool names fixed)

| Tool | Parameters | Notes |
|---|---|---|
| `claim_files` | `paths[]`, `agent_id?`, `ttl_seconds=300`, `branch?`, `wait=false` | `agent_id` defaults to env `AUTOKEREN_AGENT_ID`, else `"main"`. Ghost children pass their ghost ID explicitly (the model knows "ghost #N" from the spawn output). |
| `release_claim` | `paths?`, `agent_id?`, `request_id?`, `cancel_waiters=false` | Explicit release; idempotent. `request_id` cancels a still-queued claim. |
| `merge_queue` | `action=enqueue\|status\|dequeue`, `branch`, `paths?`, `change_id?`, `agent_id?` | |

Anchored semantics: atomic all-or-nothing claims; idempotent release; an expired lease is never
visible (sweep first on every operation); FIFO waiters are fair (promotion only from the head of
the queue whose paths are free); a stale waiter blocks nobody (it holds no resource) — production
adds `max_wait_seconds` + cleanup via DO alarms.

## File Map

- `autokeren/coord/store.py` — the claim/lease + conflict + merge-queue core (stdlib-only).
- `autokeren/tools/coord.py` — the 3 tools above, following the `Tool` ABC pattern.
- `examples/coord-demo/demo.py` — the 5-agent demo: without the layer (4 edits silently lost) vs
  with the layer (5/5 edits survive, everything recorded).
- `tests/test_coord.py` — unit tests for claim/expiry/conflict/queue + tools.

## MVP Non-goals

- No 3-way merge / line-level conflict resolution — overlap detection at path granularity.
- No fast lane for disjoint changes (production: non-overlapping changes could safely "jump"
  the FIFO; the MVP stays strictly FIFO for determinism).
- No remote Worker+DO+D1 backend in this MVP — the design above is ready to execute.
- Go-native tool parity — follow-up.
