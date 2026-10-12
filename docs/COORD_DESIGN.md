# Change Coordination Layer — Design (MVP)

Entry untuk challenge Cloudflare "Build the next GitHub". Layer koordinasi agar banyak AI
agent bisa bekerja paralel pada changes yang sama tanpa tabrakan senyap (last-write-wins).

## Problem

autokeren sudah bisa spawn banyak ghost agent paralel (`spawn_agent`, `internal/project`
worker DAG), tetapi tidak ada primitive koordinasi: dua agent yang mengedit file sama akan
saling menimpa tanpa suara. Git mendeteksi konflik terlambat (saat merge, setelah kerja
selesai terbuang). Layer ini mendeteksi POTENSI konflik sebelum edit terjadi.

## Konsep Inti

| Konsep | Definisi |
|---|---|
| **Claim / Lease** | Hak edit eksklusif atas satu path, dimiliki `agent_id`, berTTL, auto-expire, release eksplisit. Claim multi-path bersifat atomik (all-or-nothing). |
| **Conflict** | Claim pada path yang masih di-hold agent lain → respons terstruktur: pemilik, sisa TTL (detik), jumlah antrian di depan, opsi `wait=false` (fail fast) / `wait=true` (masuk FIFO). |
| **Merge queue** | Antrian FIFO per-branch dari change (set-of-paths). Change diuji overlap path dengan semua change di depannya. |
| **Event log** | Audit append-only: setiap grant/conflict/queue/promotion/release/expiry tercatat dengan timestamp. |

Status merge queue:
- `pass` — tidak ada change di depannya (head) → boleh merge sekarang.
- `queued` — ada change di depan, TIDAK overlap → aman, menunggu giliran (disiplin FIFO).
- `conflict` — overlap path dengan ≥1 change di depan → harus menunggu change itu selesai.

Setiap `dequeue` me-render ulang status semua change di belakangnya.

## API (identik untuk mode local dan produksi)

```
claim(paths, agent_id, ttl_seconds, branch?, wait) -> {granted | conflict | queued}
release(agent_id, paths?, request_id?, cancel_waiters?) -> {released, cancelled, promoted}
status(path?, agent_id?) -> {claims, waiters, queues}
queue_enqueue(branch, paths, agent_id, change_id?) -> {change_id, position, status, blocked_by}
queue_status(branch?, change_id?) -> listing + status
queue_dequeue(branch, change_id) -> removed + re-evaluasi
events(limit?) -> audit trail
```

## Arsitektur — dua backend, satu kontrak

### Mode local (MVP ini, yang bisa judge jalankan tanpa deploy)

- State disimpan di `<root>/.autokeren/coord.json` — satu file JSON, ditulis atomik
  (tmp + rename, 0600), mengikuti pola persistensi repo (`.autokeren/*.json`).
- **File adalah single source of truth**: setiap operasi (1) akuisisi `flock` pada
  `coord.json.lock`, (2) reload state dari disk, (3) mutasi, (4) tulis atomik, (5) lepas
  lock. Akibatnya ghost agent = proses OS berbeda tetap terkoordinasi lewat file —
  tidak ada shared memory sama sekali. (Fallback Windows: threading.Lock in-process;
  keterbatasan tercatat, target demo Linux/macOS.)
- **Lazy TTL sweep** di awal tiap operasi: lease kedaluwarsa dihapus (event
  `lease_expired`) lalu waiter FIFO dipromosikan bila SEMUA path yang dimintanya bebas.
- Waiter multi-path dipromosikan hanya bila seluruh set path-nya bebas (mencegah
  deadlock antar-claim multi-path).
- Event log di-cap 2000 entri terakhir agar file tetap kecil.

### Target produksi: Cloudflare Worker + Durable Objects + D1

- **Worker** — HTTP API dengan permukaan sama persis dengan API local di atas; auth pakai
  pola API key gateway yang sudah ada (`autokeren-dev-api`).
- **Durable Objects**:
  - `ClaimShardDO` (satu per project): peta claim + wait queue. Single-writer DO =
    claim/release race-free tanpa transaksi eksplisit; menggantikan `flock` local.
  - `BranchQueueDO` (satu per branch): serialisasi enqueue/dequeue + re-evaluasi status.
  - **DO alarms** menggantikan lazy sweep: alarm per lease → auto-expire push-based,
  tanpa polling, tanpa cron.
- **D1** — event log append-only + riwayat queue (audit/analytics per-project), config.
- **Kenapa DO + D1, bukan KV/R2**: koordinasi claim butuh linearizability — KV hanya
  eventually consistent (dua agent bisa sama-sama "dapat" lease). DO memberi
  single-writer + alarm bawaan; D1 memberi riwayat relasional murah tanpa ops. R2 hanya
  untuk artifact besar. desain `ClaimShardDO`/`BranchQueueDO` adalah lift langsung dari
  method `CoordStore` (klas state sama, algorithm sama, hanya medium berbeda).

## Keputusan Runtime (trade-off dicatat, tidak blocking)

**MVP diimplementasikan di Python compat layer** (`autokeren/coord/`), bukan Go native:

1. Demo WAJIB jalan `python3 examples/coord-demo/demo.py` tanpa API key/dependency —
   core stdlib-only membuat itu mungkin.
2. Kecepatan menuju deadline (14 Okt): satu runtime > dua runtime paralel.
3. Tools mendaftar di registry Python sesuai AGENTS.md (`autokeren/tools/__init__.py`).

Konsekuensi yang disadari: engine Go default belum mengekspos `claim_files` dll. Paritas
Go adalah follow-up mekanis — kontrak `internal/tool` (struct + `Definition()` +
`NeedsPermission()` + `Run()`, registrasi di `internal/engine/standalone.go:102`) dan
semantik store sudah fixed di dokumen ini; port ≈ 300 baris Go. Interfis API local ==
API HTTP Worker, sehingga mengganti backend tidak mengubah tools.

## Tools CLI (Python compat, nama tool fixed)

| Tool | Parameter | Catatan |
|---|---|---|
| `claim_files` | `paths[]`, `agent_id?`, `ttl_seconds=300`, `branch?`, `wait=false` | `agent_id` default: env `AUTOKEREN_AGENT_ID`, else `"main"`. Ghost child mempass ID ghost-nya eksplisit (model tahu "ghost #N" dari output spawn). |
| `release_claim` | `paths?`, `agent_id?`, `request_id?`, `cancel_waiters=false` | Release eksplisit; idempotent. `request_id` membatalkan claim yang masih antri. |
| `merge_queue` | `action=enqueue\|status\|dequeue`, `branch`, `paths?`, `change_id?`, `agent_id?` | |

Semantik jangkar: claim atomik all-or-nothing; release idempotent; lease yang expire tidak
pernah terlihat (sweep dulu di semua operasi); FIFO waiters adil (promosi hanya dari
kepala antrian yang path-nya bebas); waiter stale tidak memblok siapa pun (tidak memegang
resource) — produksi menambah `max_wait_seconds` + pembersihan via alarm DO.

## File Map

- `autokeren/coord/store.py` — core claim/lease + conflict + merge queue (stdlib-only).
- `autokeren/tools/coord.py` — 3 tool di atas, mengikuti pola `Tool` ABC.
- `examples/coord-demo/demo.py` — demo 5 agent: tanpa layer (4 edit hilang senyap) vs
  dengan layer (5/5 edit selamat, semua kejadian tercatat).
- `tests/test_coord.py` — unit test claim/expiry/conflict/queue + tools.

## Non-goal MVP

- Tidak ada merge 3-way / resolusi konflik level baris — deteksi overlap pada granularitas path.
- Tidak ada fast-lane antrean untuk change disjoint (produksi: change non-overlap bisa
  "melompati" FIFO dengan aman; MVP tetap strict FIFO demi determinisme).
- Tidak ada backend remote Worker+DO+D1 dalam MVP ini — desain di atas siap dieksekusi.
- Paritas tool Go-native — follow-up.
