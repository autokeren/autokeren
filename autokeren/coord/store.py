"""Change Coordination Layer — claim/lease, deteksi konflik, dan merge queue.

Mode local: seluruh state disimpan dalam satu file JSON (`.autokeren/coord.json`)
yang diamankan flock lintas-proses; file adalah single source of truth sehingga
agent berupa proses OS terpisah tetap terkoordinasi. Lihat docs/COORD_DESIGN.md
untuk semantik lengkap dan target produksi (Worker + Durable Objects + D1).
"""
from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

DEFAULT_TTL_SECONDS = 300.0
EVENT_LIMIT = 2000
LOCK_TIMEOUT_SECONDS = 10.0


class CoordLockTimeout(RuntimeError):
    """Gagal mengambil lock koordinasi dalam batas waktu."""


def _acquire_flock(fd: int, timeout_seconds: float) -> None:
    if fcntl is None:
        return
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise CoordLockTimeout(f"lock koordinasi tidak lepas dalam {timeout_seconds:g}s")
            time.sleep(0.02)


def _empty_state() -> dict[str, Any]:
    return {"claims": {}, "waiters": [], "queues": {}, "events": [], "next_id": 1}


def _emit(state: dict[str, Any], kind: str, agent_id: str, paths: list[str], detail: str = "") -> None:
    state["events"].append(
        {"ts": round(time.time(), 3), "kind": kind, "agent_id": agent_id, "paths": paths, "detail": detail}
    )
    if len(state["events"]) > EVENT_LIMIT:
        del state["events"][: len(state["events"]) - EVENT_LIMIT]


def _normalize_paths(paths: list[str]) -> list[str]:
    unique: list[str] = []
    for raw in paths:
        p = str(raw).strip().replace("\\", "/")
        while p.startswith("./"):
            p = p[2:]
        if p.startswith("/") or ".." in p.split("/"):
            raise ValueError(f"path harus relatif terhadap project root: {raw!r}")
        if p and p not in unique:
            unique.append(p)
    if not unique:
        raise ValueError("daftar path kosong")
    return unique


def _sweep(state: dict[str, Any], now: float) -> None:
    expired = [p for p, c in state["claims"].items() if float(c["expires_at"]) <= now]
    for p in expired:
        claim = state["claims"].pop(p)
        _emit(state, "lease_expired", claim["agent_id"], [p], f"claim_id={claim['claim_id']} TTL habis")
    if expired:
        _promote_waiters(state, now)


def _grant(
    state: dict[str, Any],
    now: float,
    paths: list[str],
    agent_id: str,
    branch: str | None,
    ttl_seconds: float,
    from_queue: bool,
) -> str:
    claim_id = f"c-{state['next_id']}"
    state["next_id"] = int(state["next_id"]) + 1
    expires_at = now + ttl_seconds
    for p in paths:
        state["claims"][p] = {
            "claim_id": claim_id,
            "agent_id": agent_id,
            "branch": branch,
            "acquired_at": now,
            "expires_at": expires_at,
            "ttl_seconds": ttl_seconds,
        }
    kind = "lease_granted_from_queue" if from_queue else "lease_granted"
    _emit(state, kind, agent_id, paths, f"claim_id={claim_id} ttl={ttl_seconds:g}s branch={branch or '-'}")
    return claim_id


def _promote_waiters(state: dict[str, Any], now: float) -> list[dict[str, Any]]:
    granted: list[dict[str, Any]] = []
    progressed = True
    while progressed:
        progressed = False
        for idx, waiter in enumerate(state["waiters"]):
            earlier = state["waiters"][:idx]
            if any(set(w["paths"]) & set(waiter["paths"]) for w in earlier):
                continue
            if all(p not in state["claims"] for p in waiter["paths"]):
                state["waiters"].remove(waiter)
                claim_id = _grant(
                    state,
                    now,
                    waiter["paths"],
                    waiter["agent_id"],
                    waiter.get("branch"),
                    float(waiter["ttl_seconds"]),
                    from_queue=True,
                )
                granted.append(
                    {
                        "request_id": waiter["request_id"],
                        "agent_id": waiter["agent_id"],
                        "paths": waiter["paths"],
                        "claim_id": claim_id,
                    }
                )
                progressed = True
                break
    return granted


class CoordStore:
    """Fasad stateless di atas file koordinasi; satu instance per proses aman."""

    def __init__(self, root: str | Path, state_relpath: str = ".autokeren/coord.json") -> None:
        self.root = Path(root)
        self.state_path = self.root / state_relpath
        self._thread_lock = threading.Lock()

    @contextmanager
    def _transaction(self) -> Iterator[dict[str, Any]]:
        with self._thread_lock:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(self.state_path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
            try:
                _acquire_flock(fd, LOCK_TIMEOUT_SECONDS)
                state = self._load()
                yield state
                self._save(state)
            finally:
                if fcntl is not None:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
                os.close(fd)

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return _empty_state()
        if not isinstance(raw, dict):
            return _empty_state()
        base = _empty_state()
        for key, value in base.items():
            raw.setdefault(key, value)
        return raw

    def _save(self, state: dict[str, Any]) -> None:
        tmp = str(self.state_path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.state_path)

    def claim(
        self,
        paths: list[str],
        agent_id: str,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        branch: str | None = None,
        wait: bool = False,
    ) -> dict[str, Any]:
        norm = _normalize_paths(paths)
        agent = str(agent_id).strip() or "main"
        ttl = float(ttl_seconds)
        if ttl <= 0:
            raise ValueError("ttl_seconds harus > 0")
        with self._transaction() as state:
            now = time.time()
            _sweep(state, now)
            held: dict[str, dict[str, Any]] = {}
            renewed: list[str] = []
            for p in norm:
                c = state["claims"].get(p)
                if c is None:
                    continue
                if str(c["agent_id"]) == agent:
                    renewed.append(p)
                else:
                    held[p] = c
            if not held:
                claim_id = _grant(state, now, norm, agent, branch, ttl, from_queue=False)
                if renewed:
                    _emit(state, "lease_renewed", agent, renewed, f"TTL di-refresh ke {ttl:g}s")
                return {
                    "status": "granted",
                    "acquired": True,
                    "claim_id": claim_id,
                    "agent_id": agent,
                    "paths": norm,
                    "branch": branch,
                    "ttl_seconds": ttl,
                    "expires_in_seconds": round(ttl, 1),
                }
            conflicts = [
                {
                    "path": p,
                    "owner": c["agent_id"],
                    "claim_id": c["claim_id"],
                    "remaining_seconds": max(0.0, round(float(c["expires_at"]) - now, 1)),
                }
                for p, c in sorted(held.items())
            ]
            waiters_ahead = sum(1 for w in state["waiters"] if set(w["paths"]) & set(held))
            retry_after = min(c["remaining_seconds"] for c in conflicts)
            if not wait:
                _emit(
                    state,
                    "claim_conflict",
                    agent,
                    norm,
                    "; ".join(f"{c['path']} dipegang {c['owner']} (sisa {c['remaining_seconds']}s)" for c in conflicts),
                )
                return {
                    "status": "conflict",
                    "acquired": False,
                    "agent_id": agent,
                    "paths": norm,
                    "conflicts": conflicts,
                    "waiters_ahead": waiters_ahead,
                    "options": {
                        "wait": "ulangi dengan wait=true untuk masuk antrian FIFO",
                        "retry_after_seconds": retry_after,
                    },
                }
            request_id = f"w-{state['next_id']}"
            state["next_id"] = int(state["next_id"]) + 1
            state["waiters"].append(
                {
                    "request_id": request_id,
                    "agent_id": agent,
                    "paths": norm,
                    "branch": branch,
                    "ttl_seconds": ttl,
                    "enqueued_at": now,
                }
            )
            _emit(
                state,
                "claim_queued",
                agent,
                norm,
                f"request_id={request_id} di belakang {waiters_ahead} waiter",
            )
            return {
                "status": "queued",
                "acquired": False,
                "request_id": request_id,
                "agent_id": agent,
                "paths": norm,
                "conflicts": conflicts,
                "waiters_ahead": waiters_ahead,
                "estimated_wait_seconds": round(retry_after + waiters_ahead * retry_after, 1),
            }

    def release(
        self,
        agent_id: str,
        paths: list[str] | None = None,
        request_id: str | None = None,
        cancel_waiters: bool = False,
    ) -> dict[str, Any]:
        agent = str(agent_id).strip() or "main"
        targets = _normalize_paths(paths) if paths else None
        with self._transaction() as state:
            now = time.time()
            _sweep(state, now)
            released: list[str] = []
            for p in list(state["claims"]):
                c = state["claims"][p]
                if str(c["agent_id"]) == agent and (targets is None or p in targets):
                    del state["claims"][p]
                    released.append(p)
            cancelled: list[str] = []
            drop_all = targets is None and request_id is None
            for w in list(state["waiters"]):
                mine = str(w["agent_id"]) == agent
                hits_request = request_id is not None and w["request_id"] == request_id
                if mine and (drop_all or cancel_waiters or hits_request):
                    state["waiters"].remove(w)
                    cancelled.append(w["request_id"])
                    _emit(state, "claim_cancelled", agent, w["paths"], f"request_id={w['request_id']}")
            if released:
                _emit(state, "lease_released", agent, sorted(released), "lease dilepas eksplisit")
            promoted = _promote_waiters(state, now) if (released or cancelled) else []
            return {"released": sorted(released), "cancelled": cancelled, "promoted": promoted}

    def status(self, path: str | None = None, agent_id: str | None = None) -> dict[str, Any]:
        with self._transaction() as state:
            now = time.time()
            _sweep(state, now)
            filter_path = _normalize_paths([path])[0] if path else None
            claims = []
            for p, c in sorted(state["claims"].items()):
                if filter_path and p != filter_path:
                    continue
                if agent_id and str(c["agent_id"]) != agent_id:
                    continue
                claims.append(
                    {
                        "path": p,
                        "agent_id": c["agent_id"],
                        "claim_id": c["claim_id"],
                        "branch": c.get("branch"),
                        "remaining_seconds": max(0.0, round(float(c["expires_at"]) - now, 1)),
                    }
                )
            waiters = [
                {"request_id": w["request_id"], "agent_id": w["agent_id"], "paths": w["paths"], "position": i + 1}
                for i, w in enumerate(state["waiters"])
            ]
            queues: dict[str, list[dict[str, Any]]] = {}
            for b in sorted(state["queues"]):
                queues[b] = self._evaluate_queue(state, b)
            return {"claims": claims, "waiters": waiters, "queues": queues}

    def _evaluate_queue(self, state: dict[str, Any], branch: str) -> list[dict[str, Any]]:
        q = state["queues"].get(branch, [])
        for i, entry in enumerate(q):
            blocked = []
            for other in q[:i]:
                shared = sorted(set(other["paths"]) & set(entry["paths"]))
                if shared:
                    blocked.append(
                        {"change_id": other["change_id"], "agent_id": other["agent_id"], "shared_paths": shared}
                    )
            blocked_ids = [b["change_id"] for b in blocked]
            new_status = "conflict" if blocked else ("queued" if i > 0 else "pass")
            entry["blocked_by"] = blocked_ids
            entry["conflicts"] = blocked
            if entry.get("status") != new_status:
                old = str(entry.get("status") or "baru")
                entry["status"] = new_status
                _emit(
                    state,
                    "queue_status",
                    entry["agent_id"],
                    entry["paths"],
                    f"{entry['change_id']}: {old} -> {new_status} (branch {branch})",
                )
        return [
            {
                "change_id": e["change_id"],
                "agent_id": e["agent_id"],
                "paths": e["paths"],
                "status": e["status"],
                "position": i + 1,
                "blocked_by": e["blocked_by"],
                "conflicts": e.get("conflicts", []),
                "enqueued_at": e["enqueued_at"],
            }
            for i, e in enumerate(q)
        ]

    def queue_enqueue(
        self,
        branch: str,
        paths: list[str],
        agent_id: str,
        change_id: str | None = None,
    ) -> dict[str, Any]:
        b = str(branch).strip()
        if not b:
            raise ValueError("branch wajib diisi")
        norm = _normalize_paths(paths)
        agent = str(agent_id).strip() or "main"
        with self._transaction() as state:
            now = time.time()
            _sweep(state, now)
            q = state["queues"].setdefault(b, [])
            cid = str(change_id).strip() if change_id else f"mq-{state['next_id']}"
            state["next_id"] = int(state["next_id"]) + 1
            if any(e["change_id"] == cid for e in q):
                raise ValueError(f"change_id sudah dipakai di queue branch {b}: {cid}")
            entry: dict[str, Any] = {
                "change_id": cid,
                "agent_id": agent,
                "paths": norm,
                "branch": b,
                "enqueued_at": now,
                "status": "queued",
                "blocked_by": [],
            }
            q.append(entry)
            _emit(state, "queue_enqueued", agent, norm, f"branch={b} change_id={cid}")
            self._evaluate_queue(state, b)
            return {
                "change_id": cid,
                "branch": b,
                "position": q.index(entry) + 1,
                "queue_length": len(q),
                "status": entry["status"],
                "blocked_by": entry["blocked_by"],
                "conflicts": entry.get("conflicts", []),
            }

    def queue_status(self, branch: str | None = None, change_id: str | None = None) -> dict[str, list[dict[str, Any]]]:
        with self._transaction() as state:
            now = time.time()
            _sweep(state, now)
            branches = [str(branch)] if branch else sorted(state["queues"])
            out: dict[str, list[dict[str, Any]]] = {}
            for b in branches:
                if b not in state["queues"]:
                    raise ValueError(f"branch tidak punya queue: {b}")
                entries = self._evaluate_queue(state, b)
                if change_id:
                    entries = [e for e in entries if e["change_id"] == change_id]
                    if not entries:
                        raise ValueError(f"change_id tidak ditemukan di queue branch {b}: {change_id}")
                out[b] = entries
            return out

    def queue_dequeue(self, branch: str, change_id: str) -> dict[str, Any]:
        b = str(branch).strip()
        cid = str(change_id).strip()
        if not b or not cid:
            raise ValueError("branch dan change_id wajib diisi")
        with self._transaction() as state:
            now = time.time()
            _sweep(state, now)
            q = state["queues"].get(b, [])
            entry = next((e for e in q if e["change_id"] == cid), None)
            if entry is None:
                raise ValueError(f"change_id tidak ditemukan di queue branch {b}: {cid}")
            q.remove(entry)
            _emit(
                state,
                "queue_dequeued",
                entry["agent_id"],
                entry["paths"],
                f"branch={b} change_id={cid} (status saat keluar: {entry['status']})",
            )
            remaining = self._evaluate_queue(state, b)
            return {
                "removed": {"change_id": cid, "agent_id": entry["agent_id"], "status": entry["status"]},
                "queue_length": len(q),
                "queue": remaining,
            }

    def events(
        self,
        limit: int | None = None,
        kind: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        with self._transaction() as state:
            now = time.time()
            _sweep(state, now)
            evs = state["events"]
            if kind:
                evs = [e for e in evs if e["kind"] == kind]
            if agent_id:
                evs = [e for e in evs if str(e["agent_id"]) == agent_id]
            n = len(evs) if limit is None else max(0, int(limit))
            return {"events": evs[-n:], "total": len(evs)}
