#!/usr/bin/env python3
"""Change Coordination Layer demo — 5 agents racing for the same file.

Run it with no API key and no dependencies:
    python3 examples/coord-demo/demo.py

Part 1: WITHOUT the layer — 5 agents read-modify-write concurrently -> silent
        collision (last-write-wins, edits lost without a trace).
Part 2: WITH the layer — 1 agent gets the lease, 4 queue; the crashed agent's
        lease auto-expires via TTL; every event is recorded in the event log.
Part 3: per-branch merge queue — pass/queued/conflict statuses + re-evaluation.
Part 4: event log — the full audit trail.
"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from autokeren.coord.store import CoordStore  # noqa: E402

AGENTS = [f"agent-{i}" for i in range(1, 6)]
TARGET = "src/app.py"
TTL = 3.0
_print_lock = threading.Lock()


def say(text: str) -> None:
    with _print_lock:
        print(text, flush=True)


def banner(title: str) -> None:
    say("")
    say("=" * 72)
    say(f" {title}")
    say("=" * 72)


def write_file(root: Path, relpath: str, content: str) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_file(root: Path, relpath: str) -> str:
    return (root / relpath).read_text(encoding="utf-8")


def part1_no_layer(workspace: Path) -> tuple[int, int]:
    banner("[1] WITHOUT the Change Coordination Layer — status quo (silent collision)")
    say(f"5 agents read-modify-write {TARGET} concurrently (each agent appends one edit line):")
    write_file(workspace, TARGET, "# init\n")
    read_barrier = threading.Barrier(len(AGENTS))
    beliefs: dict[str, int] = {}

    def worker(agent: str, delay: float) -> None:
        content = read_file(workspace, TARGET)
        read_barrier.wait()
        time.sleep(delay)
        new_content = content + f"edit by {agent}\n"
        write_file(workspace, TARGET, new_content)
        beliefs[agent] = len(new_content.strip().splitlines())
        say(f"  {agent}: read {len(content.strip().splitlines())} line(s) -> wrote {beliefs[agent]} lines (believes success)")

    threads = [threading.Thread(target=worker, args=(a, (5 - i) * 0.03)) for i, a in enumerate(AGENTS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_lines = read_file(workspace, TARGET).strip().splitlines()
    survived = sum(1 for a in AGENTS if f"edit by {a}" in final_lines)
    say("")
    say(f"Final content of {TARGET} (the reality on disk):")
    for line in final_lines:
        say(f"    | {line}")
    say("")
    say(f"Every agent BELIEVES its edit was saved (each believes the file now has {beliefs[AGENTS[0]]} lines),")
    say(f"but what actually survived: {survived}/{len(AGENTS)} edits.")
    say(f"==> {len(AGENTS) - survived} edits SILENTLY LOST: no error, no log, no witness.")
    return survived, len(AGENTS)


def part2_with_layer(workspace: Path) -> tuple[int, int, CoordStore]:
    banner("[2] WITH the Change Coordination Layer — claim/lease + queue + event log")
    say(f"Workspace : {workspace} (temp, auto-cleaned when the demo ends)")
    say(f"State file: {workspace / '.autokeren' / 'coord.json'}")
    say("Each agent uses its OWN CoordStore instance (no shared memory) —")
    say("coordination is 100% via the file + flock, equivalent to 5 separate OS processes.")
    say("")
    write_file(workspace, TARGET, "# init\n")
    store = CoordStore(workspace)
    say(f"5 agents claim {TARGET} (lease TTL {TTL:g}s, multi-path claims are atomic):")
    store.claim([TARGET], AGENTS[0], ttl_seconds=TTL, branch="main")
    say(f"  {AGENTS[0]}: GRANTED  (gets the exclusive lease)")
    for agent in AGENTS[1:]:
        res = store.claim([TARGET], agent, ttl_seconds=TTL, branch="main", wait=True)
        owner = res["conflicts"][0]["owner"]
        remaining = res["conflicts"][0]["remaining_seconds"]
        say(
            f"  {agent}: CONFLICT ({TARGET} held by {owner}, {remaining}s of TTL left)"
            f" -> wait=true -> QUEUED (request_id={res['request_id']}, queue position {res['waiters_ahead'] + 1})"
        )

    def worker(agent: str, crash: bool = False) -> None:
        private_store = CoordStore(workspace)
        if crash:
            time.sleep(1.0)
            content = read_file(workspace, TARGET)
            write_file(workspace, TARGET, content + f"edit by {agent}\n")
            say(f"  {agent}: finished editing, then CRASHED without releasing (lease left dangling!)")
            return
        while True:
            claims = private_store.status(path=TARGET)["claims"]
            if claims and claims[0]["agent_id"] == agent:
                say(f"  {agent}: lease GRANTED from the queue (automatic FIFO promotion) -> start editing")
                break
            time.sleep(0.15)
        time.sleep(0.3)
        content = read_file(workspace, TARGET)
        write_file(workspace, TARGET, content + f"edit by {agent}\n")
        private_store.release(agent, paths=[TARGET])
        say(f"  {agent}: edit done -> explicit RELEASE -> next agent gets promoted")

    say("")
    say(f"{AGENTS[0]} starts working... (its {TTL:g}s lease will expire since it crashed without release)")
    threads = [threading.Thread(target=worker, args=(AGENTS[0], True))]
    threads += [threading.Thread(target=worker, args=(a,)) for a in AGENTS[1:]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_lines = read_file(workspace, TARGET).strip().splitlines()
    survived = sum(1 for a in AGENTS if f"edit by {a}" in final_lines)
    say("")
    say(f"Final content of {TARGET} (the reality on disk):")
    for line in final_lines:
        say(f"    | {line}")
    say("")
    say(f"All edits survived: {survived}/{len(AGENTS)}. The crashed agent's lease is auto-cleaned by the TTL,")
    say("the FIFO queue keeps flowing, and there are ZERO silent collisions.")
    return survived, len(AGENTS), store


def part3_merge_queue(store: CoordStore) -> None:
    banner("[3] BONUS: per-branch Merge Queue — overlap detected BEFORE merge")
    say("FIFO queue for branch 'main'; each change is tested for path overlap against the changes ahead of it:")
    changes = [
        ("c1", ["api/auth.py"], "agent-1"),
        ("c2", ["ui/theme.css"], "agent-2"),
        ("c3", ["api/auth.py", "api/session.py"], "agent-3"),
        ("c4", ["ui/theme.css", "ui/layout.js"], "agent-4"),
    ]
    for cid, paths, agent in changes:
        res = store.queue_enqueue("main", paths, agent, change_id=cid)
        blocked = f", blocked_by={res['blocked_by']}" if res["blocked_by"] else ""
        say(f"  enqueue {cid} {{{', '.join(paths)}}} by {agent:<8} -> {res['status'].upper()}{blocked}")

    say("")
    say("c1 finished merging (dequeued) -> the entire queue is re-evaluated:")
    store.queue_dequeue("main", "c1")
    for e in store.queue_status("main")["main"]:
        say(f"  position {e['position']}: {e['change_id']} -> {e['status'].upper()}  blocked_by={e['blocked_by']}")
    say("")
    say("c2 finished merging (dequeued):")
    store.queue_dequeue("main", "c2")
    for e in store.queue_status("main")["main"]:
        say(f"  position {e['position']}: {e['change_id']} -> {e['status'].upper()}  blocked_by={e['blocked_by']}")
    say("")
    say("Meaning: a change that overlaps paths with a change ahead of it is FLAGGED from the start")
    say("(not discovered too late at merge time), and per-branch merge order is preserved.")


def part4_event_log(store: CoordStore, t0: float) -> None:
    banner("[4] Event Log — everything recorded (audit trail)")
    res = store.events(limit=40)
    say(f"Total events since the demo started: {res['total']} (showing up to the last 40):")
    for e in res["events"]:
        rel = e["ts"] - t0
        line = f"  t+{rel:6.2f}s  {e['kind']:<24} {e['agent_id']:<10} {', '.join(e['paths'])}"
        if e["detail"]:
            line += f" | {e['detail']}"
        say(line)
    say("")
    say("Without the layer: 0 events recorded. With the layer: every grant, conflict, queue,")
    say("promotion, release, and expiry leaves a timestamped, auditable trace.")


def main() -> None:
    t0 = time.time()
    print(
        """
========================================================================
  Cloudflare "Build the next GitHub" — Change Coordination Layer (MVP)
  5 AI agents, 1 shared file: with vs without coordination
========================================================================""",
        flush=True,
    )
    with tempfile.TemporaryDirectory(prefix="coord-demo-") as tmp:
        workspace = Path(tmp)
        survived1, total = part1_no_layer(workspace)
        write_file(workspace, TARGET, "# init\n")
        survived2, _, store = part2_with_layer(workspace)
        part3_merge_queue(store)
        part4_event_log(store, t0)
        banner("CONCLUSION")
        say(f"  WITHOUT layer : {survived1}/{total} edits survived, {total - survived1} silently lost, 0 events recorded.")
        say(f"  WITH layer    : {survived2}/{total} edits survived, 0 lost, crashed lease auto-cleaned by TTL.")
        fresh = CoordStore(workspace)
        say(f"  Persistence proof: a NEW CoordStore instance sees the same {fresh.events()['total']} events")
        say("  (state lives in the file, not in memory — a restart does not lose coordination).")
        say("")
        say("Production design: Cloudflare Worker + Durable Objects (single-writer claims/queues")
        say("+ TTL alarms) + D1 (audit). Details: docs/COORD_DESIGN.md")


if __name__ == "__main__":
    main()
