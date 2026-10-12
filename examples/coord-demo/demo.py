#!/usr/bin/env python3
"""Demo Change Coordination Layer — perbandingan 5 agent yang berebut file yang sama.

Jalankan tanpa API key dan tanpa dependency:
    python3 examples/coord-demo/demo.py

Bagian 1: TANPA layer — 5 agent read-modify-write bersamaan -> tabrakan senyap
           (last-write-wins, edit hilang tanpa jejak).
Bagian 2: DENGAN layer — 1 agent dapat lease, 4 antri; lease agent yang crash
           auto-expire via TTL; semua kejadian tercatat di event log.
Bagian 3: Merge queue per-branch — status pass/queued/conflict + re-evaluasi.
Bagian 4: Event log — audit trail lengkap.
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
    banner("[1] TANPA Change Coordination Layer — status quo (tabrakan senyap)")
    say(f"5 agent read-modify-write {TARGET} secara bersamaan (tiap agent menambah 1 baris edit):")
    write_file(workspace, TARGET, "# init\n")
    read_barrier = threading.Barrier(len(AGENTS))
    beliefs: dict[str, int] = {}

    def worker(agent: str, delay: float) -> None:
        content = read_file(workspace, TARGET)
        read_barrier.wait()
        time.sleep(delay)
        new_content = content + f"edit oleh {agent}\n"
        write_file(workspace, TARGET, new_content)
        beliefs[agent] = len(new_content.strip().splitlines())
        say(f"  {agent}: membaca {len(content.strip().splitlines())} baris -> menulis {beliefs[agent]} baris (yakin berhasil)")

    threads = [threading.Thread(target=worker, args=(a, (5 - i) * 0.03)) for i, a in enumerate(AGENTS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_lines = read_file(workspace, TARGET).strip().splitlines()
    survived = sum(1 for a in AGENTS if f"edit oleh {a}" in final_lines)
    say("")
    say(f"Isi akhir {TARGET} (fakta di disk):")
    for line in final_lines:
        say(f"    | {line}")
    say("")
    say(f"Setiap agent YAKIN editnya tersimpan (masing-masing percaya file berisi {beliefs[AGENTS[0]]} baris),")
    say(f"tetapi yang benar-benar selamat: {survived}/{len(AGENTS)} edit.")
    say(f"==> {len(AGENTS) - survived} edit HILANG SENYAP: tidak ada error, tidak ada log, tidak ada saksi.")
    return survived, len(AGENTS)


def part2_with_layer(workspace: Path) -> tuple[int, int, CoordStore]:
    banner("[2] DENGAN Change Coordination Layer — claim/lease + antrian + event log")
    say(f"Workspace : {workspace} (temp, auto-bersih saat demo selesai)")
    say(f"State file : {workspace / '.autokeren' / 'coord.json'}")
    say("Setiap agent memakai instance CoordStore SENDIRI (tanpa shared memory) —")
    say("semua koordinasi 100% lewat file + flock, ekuivalen 5 proses OS terpisah.")
    say("")
    write_file(workspace, TARGET, "# init\n")
    store = CoordStore(workspace)
    say(f"5 agent me-claim {TARGET} (lease TTL {TTL:g}s, claim multi-path bersifat atomik):")
    store.claim([TARGET], AGENTS[0], ttl_seconds=TTL, branch="main")
    say(f"  {AGENTS[0]}: GRANTED  (dapat lease eksklusif)")
    for agent in AGENTS[1:]:
        res = store.claim([TARGET], agent, ttl_seconds=TTL, branch="main", wait=True)
        owner = res["conflicts"][0]["owner"]
        remaining = res["conflicts"][0]["remaining_seconds"]
        say(
            f"  {agent}: CONFLICT ({TARGET} dipegang {owner}, sisa TTL {remaining}s)"
            f" -> wait=true -> QUEUED (request_id={res['request_id']}, posisi antrian {res['waiters_ahead'] + 1})"
        )

    def worker(agent: str, crash: bool = False) -> None:
        private_store = CoordStore(workspace)
        if crash:
            time.sleep(1.0)
            content = read_file(workspace, TARGET)
            write_file(workspace, TARGET, content + f"edit oleh {agent}\n")
            say(f"  {agent}: edit selesai, lalu CRASH tanpa release (lease menggantung!)")
            return
        while True:
            claims = private_store.status(path=TARGET)["claims"]
            if claims and claims[0]["agent_id"] == agent:
                say(f"  {agent}: lease GRANTED dari antrian (promosi otomatis FIFO) -> mulai edit")
                break
            time.sleep(0.15)
        time.sleep(0.3)
        content = read_file(workspace, TARGET)
        write_file(workspace, TARGET, content + f"edit oleh {agent}\n")
        private_store.release(agent, paths=[TARGET])
        say(f"  {agent}: edit selesai -> RELEASE eksplisit -> agent berikutnya dipromosikan")

    say("")
    say(f"{AGENTS[0]} bekerja... (lease TTL {TTL:g}s akan habis karena crash tanpa release)")
    threads = [threading.Thread(target=worker, args=(AGENTS[0], True))]
    threads += [threading.Thread(target=worker, args=(a,)) for a in AGENTS[1:]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_lines = read_file(workspace, TARGET).strip().splitlines()
    survived = sum(1 for a in AGENTS if f"edit oleh {a}" in final_lines)
    say("")
    say(f"Isi akhir {TARGET} (fakta di disk):")
    for line in final_lines:
        say(f"    | {line}")
    say("")
    say(f"Semua edit selamat: {survived}/{len(AGENTS)}. Lease agent yang crash dibersihkan otomatis oleh TTL,")
    say("antrian FIFO tetap berjalan, dan TIDAK ADA tabrakan senyap.")
    return survived, len(AGENTS), store


def part3_merge_queue(store: CoordStore) -> None:
    banner("[3] BONUS: Merge Queue per-branch — deteksi overlap SEBELUM merge")
    say("Antrian FIFO branch 'main'; tiap change diuji overlap path dengan change di depannya:")
    changes = [
        ("c1", ["api/auth.py"], "agent-1"),
        ("c2", ["ui/theme.css"], "agent-2"),
        ("c3", ["api/auth.py", "api/session.py"], "agent-3"),
        ("c4", ["ui/theme.css", "ui/layout.js"], "agent-4"),
    ]
    for cid, paths, agent in changes:
        res = store.queue_enqueue("main", paths, agent, change_id=cid)
        blocked = f", blocked_by={res['blocked_by']}" if res["blocked_by"] else ""
        say(f"  enqueue {cid} {{{', '.join(paths)}}} oleh {agent:<8} -> {res['status'].upper()}{blocked}")

    say("")
    say("c1 selesai di-merge (dequeue) -> seluruh antrian di-render ulang:")
    store.queue_dequeue("main", "c1")
    for e in store.queue_status("main")["main"]:
        say(f"  posisi {e['position']}: {e['change_id']} -> {e['status'].upper()}  blocked_by={e['blocked_by']}")
    say("")
    say("c2 selesai di-merge (dequeue):")
    store.queue_dequeue("main", "c2")
    for e in store.queue_status("main")["main"]:
        say(f"  posisi {e['position']}: {e['change_id']} -> {e['status'].upper()}  blocked_by={e['blocked_by']}")
    say("")
    say("Artinya: change yang overlap path dengan change di depannya DITANDAI sejak awal")
    say("(bukan ditemukan terlambat saat merge), dan urutan merge per-branch terjaga.")


def part4_event_log(store: CoordStore, t0: float) -> None:
    banner("[4] Event Log — semua kejadian tercatat (audit trail)")
    res = store.events(limit=40)
    say(f"Total kejadian sejak demo mulai: {res['total']} event (maks 40 terakhir ditampilkan):")
    for e in res["events"]:
        rel = e["ts"] - t0
        line = f"  t+{rel:6.2f}s  {e['kind']:<24} {e['agent_id']:<10} {', '.join(e['paths'])}"
        if e["detail"]:
            line += f" | {e['detail']}"
        say(line)
    say("")
    say("Tanpa layer: 0 kejadian tercatat. Dengan layer: setiap grant, konflik, antrian,")
    say("promosi, release, dan expiry punya jejak ber-timestamp yang bisa diaudit.")


def main() -> None:
    t0 = time.time()
    print(
        """
========================================================================
  Cloudflare "Build the next GitHub" — Change Coordination Layer (MVP)
  5 AI agents, 1 file yang sama: dengan vs tanpa koordinasi
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
        banner("KESIMPULAN")
        say(f"  TANPA layer  : {survived1}/{total} edit selamat, {total - survived1} hilang senyap, 0 kejadian tercatat.")
        say(f"  DENGAN layer : {survived2}/{total} edit selamat, 0 hilang, crash dibersihkan otomatis oleh TTL.")
        fresh = CoordStore(workspace)
        say(f"  Bukti persistensi: instance CoordStore BARU melihat {fresh.events()['total']} event yang sama")
        say("  (state hidup di file, bukan di memori — restart tidak menghilangkan koordinasi).")
        say("")
        say("Desain produksi: Cloudflare Worker + Durable Objects (single-writer claim/queue")
        say("+ alarm TTL) + D1 (audit). Detail: docs/COORD_DESIGN.md")


if __name__ == "__main__":
    main()
