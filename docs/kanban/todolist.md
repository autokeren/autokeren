# Todo List & Progress Tracker: Ak-Kanban

Dokumen ini melacak progres pengerjaan fitur Kanban Board SQLite secara real-time.

---

## 📋 Progress Board

### 🟦 Fase 1: Persiapan & Desain [100%]
- [x] Diskusi konsep utama dengan User (`docs/kanban/journey.md`)
- [x] Pembuatan spesifikasi teknis database & RPC API (`docs/kanban/runbook.md`)
- [x] Inisialisasi file checklist progres (`docs/kanban/todolist.md`)

### 🟩 Fase 2: Backend Python & Database SQLite [100%]
- [x] Buat helper database SQLite (`autokeren/kanban/db.py`)
- [x] Tulis unit test SQLite database (`tests/test_kanban_db.py`)
- [x] Buat class `KanbanTool` di `autokeren/tools/kanban.py`
- [x] Daftarkan `KanbanTool` di `autokeren/tools/__init__.py`
- [x] Tulis unit test untuk `KanbanTool`
- [x] Ekspos method JSON-RPC kanban di `autokeren/daemon.py`
- [x] Jalankan mypy & ruff check untuk memastikan kualitas kode Python

### 🟨 Fase 3: Frontend Go TUI [100%]
- [x] Definisikan struct `KanbanTask` di `ui/layout.go` atau file terpisah
- [x] Buat layout layout.go menerima input toggling `/board` atau tombol `Tab`
- [x] Implementasikan tampilan kolom Kanban horizontal dengan Lipgloss di `ui/kanban.go`
- [x] Integrasikan RPC handler untuk `kanban.list`, `kanban.add`, `kanban.move`, dan `kanban.delete`
- [x] Hubungkan update periodik agar board Kanban ter-refresh real-time via `pollPeriodicCmd`
- [x] Uji navigasi keyboard (Arrow keys, Space, Enter, a, d, x)
- [x] Pastikan cross-compilation berjalan bersih di semua platform (Windows, Linux, macOS)
