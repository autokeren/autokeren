# 📋 Todo List Pengembangan Autokeren Proof (Build Week 2026 Extension)

Dokumen ini berisi rencana pengembangan langkah demi langkah untuk mengimplementasikan **Autokeren Proof**: ekstensi alur kerja rilis berbasis bukti untuk OpenAI Build Week 2026.

---

## 🛠️ Ringkasan Fitur & Lokasi Kode Terkait

| Fitur | Status | File Utama Terkait |
| :--- | :---: | :--- |
| **1. Handoff Documentation** | ⏳ Rencana | `docs/BUILD_WEEK_2026_HANDOFF.md` |
| **2. Native `ProofTool`** | ⏳ Rencana | `autokeren/tools/proof.py` |
| **3. Slash Command `/proof`** | ⏳ Rencana | `autokeren/cli.py` |
| **4. Unit Tests** | ⏳ Rencana | `tests/test_proof.py` |
| **5. Demo Application & Replay** | ⏳ Rencana | `examples/proof-demo/` |
| **6. README Update** | ⏳ Rencana | `README.md`, `README.id.md` |

---

## 🚀 Rencana Eksekusi Langkah-Demi-Langkah

### 📌 FASE 1: Dokumentasi Handoff Publik
- [ ] **Langkah 1.1: Copy Handoff Doc**
  - Salin berkas `docs/private/BUILD_WEEK_2026_HANDOFF.md` ke folder publik `docs/BUILD_WEEK_2026_HANDOFF.md`.
  - Daftarkan berkas ini di Git tracking.

---

### 📌 FASE 2: Native Proof Tool (`autokeren/tools/proof.py`)
Tujuan: Membangun mekanisme pencatatan bukti (*evidence ledger*) yang menyimpan status verifikasi setiap kriteria penerimaan proyek.

- [ ] **Langkah 2.1: Model Data JSON & Inisialisasi**
  - Tentukan skema berkas JSON bukti di `.autokeren/proofs/<proof-id>.json`.
  - Otomatis catat `source_commit` saat inisialisasi menggunakan Git SHA saat itu (`git rev-parse HEAD`).
  - Status kriteria yang valid: `pending`, `passed`, `failed`, `blocked`, `manual_review`.

- [ ] **Langkah 2.2: Logika Penilaian (Verdict Engine)**
  - Terapkan logika penentuan keputusan:
    - Jika ada kriteria `failed` atau `blocked` $\rightarrow$ `BLOCKED`.
    - Jika tidak ada kegagalan tetapi ada `manual_review` $\rightarrow$ `NEEDS_HUMAN_REVIEW`.
    - Jika semua kriteria berstatus `passed` $\rightarrow$ `SHIP`.
    - Lainnya $\rightarrow$ `IN_PROGRESS`.

- [ ] **Langkah 2.3: Rich Formatting Report (Visual Presentation)**
  - Gunakan `rich.table` dan `rich.panel` untuk merender kartu rilis yang sangat estetik dan berwarna (hijau untuk passed, merah untuk failed/blocked, kuning untuk manual_review).

---

### 📌 FASE 3: Slash Command & Registrasi TUI
Tujuan: Mendaftarkan `ProofTool` ke registry global dan membuat parser command `/proof`.

- [ ] **Langkah 3.1: Registrasi `ProofTool`**
  - Daftarkan instansiasi `ProofTool(project_root)` di `build_registry()` dalam `autokeren/cli.py`.
  - Ekspor `ProofTool` di `autokeren/tools/__init__.py`.

- [ ] **Langkah 3.2: Parser Slash Command `/proof`**
  - Tambahkan penanganan perintah `/proof` di loop interaktif `cli.py` dan `tui.py`:
    - `/proof plan <title> | <criterion 1> | ...`
    - `/proof record <proof-id> <criterion-num> <status> | <evidence>`
    - `/proof list`
    - `/proof report <proof-id>`

---

### 📌 FASE 4: Penulisan Unit Test (`tests/test_proof.py`)
Tujuan: Memastikan fungsionalitas tool dan pembagian keputusan (verdict) berfungsi dengan benar tanpa bug regresi.

- [ ] **Langkah 4.1: Implementasi Tes**
  - Tes pembuatan rencana bukti (`plan`) baru dan penolakan argumen yang tidak lengkap.
  - Tes penyimpanan berkas JSON di folder sementara.
  - Tes logika verdict: semua passed $\rightarrow$ `SHIP`, ada failed $\rightarrow$ `BLOCKED`, ada manual_review $\rightarrow$ `NEEDS_HUMAN_REVIEW`.
  - Tes integrasi registry.

---

### 📌 FASE 5: Pembuatan Aplikasi Demo (`examples/proof-demo/`)
Tujuan: Menyediakan skenario nyata yang dapat dievaluasi oleh juri tanpa memerlukan API key OpenAI.

- [ ] **Langkah 5.1: Contoh Kasus Defect & Fitur Validasi**
  - Buat aplikasi web/API kecil dengan defect (misal: endpoint sign-up tanpa validasi email).
  - Tulis test suite mini yang mendeteksi bug ini.
  - Sediakan rekaman file bukti `.json` hasil replay agar juri bisa melihat log alur kerja rilis dari awal hingga `SHIP`.

---

### 📌 FASE 6: Pembaruan README & Dokumentasi Rilis
- [ ] **Langkah 6.1: Menulis Bab Build Week**
  - Perbarui `README.md` dan `README.id.md` dengan pengungkapan Build Week, daftar file yang dimodifikasi selama hackathon, dan cara menjalankan demo.
