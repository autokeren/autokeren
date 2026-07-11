# User Journey & Interface Design: Ak-Kanban

Dokumen ini menjelaskan alur interaksi pengguna (User) dan AI Agent (Autokeren) dengan Kanban Board, serta visualisasi antarmuka terminal.

---

## 1. Alur Pengguna (User Journey)

### Skenario A: Kolaborasi Task dengan Agen AI (Autonomous Flow)
1. **User** memberikan instruksi besar: `"buatkan backend API dengan login & CRUD user"`.
2. **Agen** menganalisis tugas tersebut, lalu memanggil `KanbanTool` di background untuk membuat sub-task di database SQLite:
   * 🎯 [Todo] `Desain database schema`
   * 🎯 [Todo] `Implementasi JWT token authentication`
   * 🎯 [Todo] `Buat REST endpoints CRUD`
   * 🎯 [Todo] `Tulis unit test`
3. TUI otomatis memuat sub-task tersebut di sidebar dan Kanban board.
4. **Agen** mulai memproses task pertama (`Desain database schema`) dan memindahkannya ke **In Progress** ⚡.
5. User melihat kartu `Desain database schema` berpindah sendiri ke kolom tengah secara *real-time*.
6. Setelah selesai, Agen menjalankannya, lalu memindahkannya ke **Done** ✅, dan memproses task berikutnya.

### Skenario B: Manajemen Mandiri oleh User (Interactive Flow)
1. User menekan tombol `Tab` atau mengetik `/board` untuk beralih dari Chat View ke **Kanban View**.
2. Chat area digantikan oleh papan horizontal yang memuat 3 kolom: **Todo**, **In Progress**, dan **Done**.
3. User menggunakan `←` / `→` untuk memilih kolom, dan `↑` / `↓` untuk memilih kartu di dalam kolom.
4. User menekan `Space` pada kartu terpilih, dan kartu tersebut langsung berpindah ke kolom berikutnya.
5. User menekan `a` untuk menambah kartu baru, mengetikkan judul tugas, lalu menekan `Enter`. Kartu baru otomatis masuk ke kolom **Todo**.
6. User menekan `Tab` lagi untuk kembali berdiskusi dengan AI Agent.

---

## 2. Visualisasi Desain Antarmuka (TUI Mockup)

### Kanban View (`/board` Mode)

```text
┌─ autokeren v0.11.0 ───────────────────────────────────────────┐
│  project: autokeren                                           │
│  model: Kimi-K2.7-Code                                        │
│  ───────────────────────────────────────────────────────────  │
│  [🎯 TODO (3)]          [⚡ IN PROGRESS (1)]    [✅ DONE (2)]    │
│ ┌──────────────────────┐ ┌────────────────────┐ ┌───────────┐ │
│ │ #1 Implementasi JWT  │ │*#3 Desain database │ │ #2 Setup  │ │
│ │  [Priority: High]    │ │  [Priority: High]  │ │   project │ │
│ └──────────────────────┘ └────────────────────┘ └───────────┘ │
│ ┌──────────────────────┐                        ┌───────────┐ │
│ │ #4 Tulis unit test   │                        │ #5 Buat   │ │
│ │  [Priority: Medium]  │                        │   readme  │ │
│ └──────────────────────┘                        └───────────┘ │
│ ┌──────────────────────┐                                      │
│ │ #6 Buat REST CRUD    │                                      │
│ │  [Priority: Medium]  │                                      │
│ └──────────────────────┘                                      │
│                                                               │
│ ── Navigasi ───────────────────────────────────────────────── │
│ ↑↓/←→: Pilih kartu  · Space: Pindah Kolom  · a: Tambah        │
│ e: Edit             · d/x: Hapus           · Tab: Kembali     │
└───────────────────────────────────────────────────────────────┘
```
*\*Catatan: Tanda bintang (*) menunjukkan kartu yang sedang dipilih (hover).*

---

## 3. Skema Kontrol Keyboard (Keybindings)

| Tombol | Aksi |
|---|---|
| `Tab` / `/board` | Toggle (beralih) antara Chat View dan Kanban View |
| `←` / `→` | Berpindah kolom aktif |
| `↑` / `↓` | Navigasi vertikal memilih kartu di kolom aktif |
| `Space` | Pindahkan kartu aktif ke kolom berikutnya (`Todo` → `In Progress` → `Done`) |
| `a` / `n` | Tambah kartu baru ke kolom `Todo` |
| `e` / `Enter` | Edit kartu terpilih (judul, deskripsi, atau prioritas) |
| `d` / `x` | Hapus kartu terpilih |
| `Esc` | Batal / keluar dari dialog input atau kembali ke Chat |
