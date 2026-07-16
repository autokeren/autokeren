# 📋 Todo List Pengembangan autokeren CLI (Arah Jenius)

Dokumen ini berisi rencana pengembangan langkah demi langkah untuk tiga fitur utama: **Repo Map Dinamis**, **Git Auto-Commit & Rollback**, dan **Live Log Sniffing & Auto-Patching**. Dokumen ini dirancang agar siapa pun (termasuk AI agent lain) bisa melanjutkan tugas jika terjadi pergantian sesi.

---

## 🛠️ Ringkasan Fitur & Lokasi Kode Terkait

| Fitur | Status | File Utama Terkait |
| :--- | :---: | :--- |
| **1. Repo Map Dinamis** | ⏳ Rencana | `autokeren/tools/repo_map.py`, `autokeren/agent.py` |
| **2. Git Auto-Commit & Rollback** | ⏳ Rencana | `autokeren/agent.py`, `autokeren/tools/git.py` |
| **3. Live Log Sniffing & Auto-Patching** | ⏳ Rencana | `autokeren/tools/tmux.py`, `autokeren/ghost/manager.py` |

---

## 🚀 Rencana Eksekusi Langkah-Demi-Langkah

### 📌 FASE 1: Sistem Repo Map Dinamis & Relevan (Semantic Relevance Mapping)
Tujuan: Menghemat token context window secara signifikan dengan mengirimkan peta codebase dinamis yang hanya berisi relasi kelas/fungsi yang relevan dengan tugas pengguna.

- [ ] **Langkah 1.1: Pembuatan Cache Index AST Lokal**
  - Buat mekanisme pemindaian cepat AST (`Abstract Syntax Tree`) seluruh file proyek saat program dimulai.
  - Simpan hasil ekstraksi (nama file, relasi kelas, fungsi, signature) ke berkas cache lokal `.ak-repomap.cache` agar tidak memindai dari nol setiap kali berjalan.
  
- [ ] **Langkah 1.2: Algoritma Pencarian & Filter Relevansi (Relevance Filtering)**
  - Di dalam `autokeren/tools/repo_map.py`, tambahkan fungsi untuk menyaring index repomap berdasarkan keyword tugas user (misal menggunakan pencarian kecocokan string/token kata kunci terbobot pada kelas & fungsi).
  - Buat relasi dependensi sederhana (jika File A mengimpor File B, maka File B harus dimasukkan ke dalam peta Mini-Repo Map).

- [ ] **Langkah 1.3: Integrasi Otomatis ke System Prompt**
  - Modifikasi `_build_system_prompt()` di `autokeren/agent.py` agar secara otomatis menjalankan Repo Map Dinamis berdasarkan input pertama user dan menyelipkannya ke bagian atas system prompt.

---

### 📌 FASE 2: Git Auto-Commit & Infinite Rollback (Self-Healing Checkpoints)
Tujuan: Menjamin keamanan kode dengan membuat titik pemulihan (*checkpoint*) otomatis per file yang dimodifikasi, dan mengembalikan kode ke kondisi terakhir yang berfungsi jika AI merusaknya.

- [ ] **Langkah 2.1: Implementasi Atomic Micro-Commit**
  - Modifikasi loop di `autokeren/agent.py` setelah tool `write_file` atau `patch_file` berhasil dieksekusi dan lolos pemeriksaan build/test.
  - Jalankan `GitAutoCommitTool` secara asinkron untuk langsung melakukan commit file tersebut.
  
- [ ] **Langkah 2.2: AI-Generated Conventional Commit Messages**
  - Buat helper di `autokeren/tools/git.py` yang meminta LLM lokal/cepat untuk merangkum ringkasan perbedaan (*diff*) menjadi pesan Conventional Commit pendek (misal: `fix(auth): handle empty email validation`).

- [ ] **Langkah 2.3: Mekanisme Auto-Rollback**
  - Jika agen mendeteksi kesalahan beruntun (misalnya linter gagal, test rusak, atau loop-breaker mendeteksi kegagalan logis), jalankan perintah `git reset --hard HEAD~1` (atau kembali ke commit tag terakhir yang berstatus "hijau") secara otomatis untuk memulihkan keadaan proyek ke kondisi terbaik sebelumnya.

---

### 📌 FASE 3: Live Log Sniffing & Auto-Patching (Supervised Self-Healing)
Tujuan: Memungkinkan agen memantau server dev di background dan memperbaiki error runtime yang muncul secara instan tanpa mengganggu kenyamanan pengguna.

- [ ] **Langkah 3.1: Log Sniffing di Sesi Tmux**
  - Kembangkan `TmuxTool` di `autokeren/tools/tmux.py` agar mendukung fungsi pemantauan berkelanjutan (*logging stream buffer*).
  - Tambahkan pustaka pendeteksi kata kunci error (seperti `TypeError`, `500 Internal Server Error`, `Exception`, `SyntaxError`) pada log output tmux.

- [ ] **Langkah 3.2: Pemicu Sub-Agent Otonom**
  - Jika log sniffer mendeteksi adanya error crash pada tmux session dev, kirim sinyal ke `autokeren/ghost/manager.py` untuk membangkitkan background sub-agent baru.
  - Sub-agent dibekali tugas spesifik: *"Perbaiki error crash [salinan log error] pada file terkait."*

- [ ] **Langkah 3.3: Verifikasi Patch & Pemulihan**
  - Setelah sub-agent melakukan perbaikan kode secara otonom, ia memicu proses reload server di tmux, membaca ulang log, dan memastikan bahwa log error tersebut telah bersih.
  - Tampilkan status di TUI utama: `"⚠️ Error runtime terdeteksi di server tmux & berhasil diperbaiki otomatis."`

---

## 📈 Petunjuk Pengujian Pengembang

Setiap kali menyelesaikan satu fase, pastikan untuk memvalidasi:
1. `ruff check .` dan `mypy autokeren` harus bebas dari peringatan/error.
2. `pytest` harus tetap lulus 100% (230 test passed).
3. Jalankan `./ak` untuk memastikan Bubble Tea TUI merender visual dengan normal tanpa lag.
