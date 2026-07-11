# Technical Runbook & Specifications: Ak-Kanban

Dokumen ini memuat spesifikasi teknis, skema database, endpoint RPC, dan alur pengerjaan implementasi Kanban Board.

---

## 1. Spesifikasi Database (SQLite)

File database ditaruh di root workspace/project dengan nama `.ak-kanban.db` agar bisa dibaca secara lokal oleh daemon Python.

### Skema Tabel: `kanban_tasks`
```sql
CREATE TABLE IF NOT EXISTS kanban_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT CHECK(status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo',
    priority TEXT CHECK(priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Spesifikasi RPC API (Python Daemon ↔ Go TUI)

Semua query database dilakukan oleh Python daemon (`autokeren/daemon.py`) dan diexpose sebagai method JSON-RPC.

### 1. `kanban.list`
*   **Request:** `{"jsonrpc": "2.0", "method": "kanban.list", "id": 1}`
*   **Response:**
    ```json
    {
      "jsonrpc": "2.0",
      "result": [
        {"id": 1, "title": "Refactor auth", "description": "JWT Auth", "status": "todo", "priority": "high"}
      ],
      "id": 1
    }
    ```

### 2. `kanban.add`
*   **Request:**
    ```json
    {
      "jsonrpc": "2.0",
      "method": "kanban.add",
      "params": {
        "title": "Tulis unit test",
        "description": "pytest tests/",
        "priority": "medium"
      },
      "id": 2
    }
    ```
*   **Response:** `{"jsonrpc": "2.0", "result": {"id": 2, "status": "success"}, "id": 2}`

### 3. `kanban.move`
*   **Request:**
    ```json
    {
      "jsonrpc": "2.0",
      "method": "kanban.move",
      "params": {"id": 1, "status": "in_progress"},
      "id": 3
    }
    ```
*   **Response:** `{"jsonrpc": "2.0", "result": {"id": 1, "status": "moved_to_in_progress"}, "id": 3}`

### 4. `kanban.delete`
*   **Request:**
    ```json
    {
      "jsonrpc": "2.0",
      "method": "kanban.delete",
      "params": {"id": 1},
      "id": 4
    }
    ```
*   **Response:** `{"jsonrpc": "2.0", "result": {"id": 1, "status": "deleted"}, "id": 4}`

---

## 3. Langkah Implementasi (Step-by-Step)

### Fase 1: Python Backend & Database
1.  Buat modul manager database di `autokeren/kanban/db.py` untuk mengelola SQLite connection, inisialisasi tabel, dan query CRUD.
2.  Implementasikan `TodoTool` upgrade atau `KanbanTool` baru di `autokeren/tools/kanban.py` agar agen AI bisa mengakses board secara native.
3.  Daftarkan tool baru di registry `autokeren/tools/__init__.py`.
4.  Daftarkan RPC method (`kanban.list`, `kanban.add`, `kanban.move`, `kanban.delete`) di `autokeren/daemon.py`.

### Fase 2: Go TUI View & Controller
1.  Tambahkan tipe data `KanbanTask` di Go side (`ui/layout.go`).
2.  Tambahkan state layout `ShowKanban` (boolean) untuk memicu pertukaran view chat ke board view.
3.  Desain component kolom Kanban menggunakan Bubble Tea & Lipgloss di file baru `ui/kanban.go`.
4.  Hubungkan keyboard event (`Tab`, `Space`, `Arrow Keys`, `a`, `d`) di `Update()` `ui/layout.go`.
5.  Modifikasi periodic polling di Go (`pollPeriodicCmd`) agar selain mengambil `agent.status`, ia juga men-query list task Kanban via RPC `kanban.list` dan memperbarui state board.

---

## 4. Rencana Pengujian (Testing Plan)

1.  **Unit Test Python:**
    *   Tulis test di `tests/test_kanban_db.py` untuk memastikan SQLite berhasil dibuat, tabel di-inisialisasi, dan CRUD berjalan tanpa error.
    *   Test `KanbanTool` untuk memastikan AI agen bisa melakukan manipulasi database via tool calls.
2.  **Lint & Type Check:**
    *   Jalankan `ruff check .` dan `mypy autokeren`.
3.  **TUI Manual Test:**
    *   Buka TUI, tekan `Tab`, tes navigasi kartu dengan keyboard.
    *   Tes tambah task dengan tombol `a` dan pindahkan dengan `Space`.
