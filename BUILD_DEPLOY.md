# Panduan Build & Deploy autokeren 🚀

Panduan ini menjelaskan arsitektur, cara build biner Go TUI, menjalankan pengujian Python daemon, kompilasi silang (cross-compile), dan melakukan perilisan versi baru secara lengkap.

---

## 1. Arsitektur Proyek
autokeren terdiri dari dua komponen utama:
1.  **Frontend (Go TUI):** Dibangun dengan Go + Bubble Tea (`charmbracelet/bubbletea`) untuk menyajikan antarmuka terminal interaktif (Chat, Kanban, dan Debate).
2.  **Backend (Python Daemon):** Mengelola komunikasi ke Cloudflare Workers AI model, manajemen status, parsing tool calls, dan penyimpanan database SQLite (`.ak-kanban.db`).

---

## 2. Persyaratan Sistem & Instalasi Dependensi
Pastikan peralatan berikut sudah terinstal di komputer Anda:
*   **Go 1.20+**
*   **Python 3.11+**
*   **ruff** (untuk linting)
*   **mypy** (untuk type-checking)
*   **pytest** (untuk pengujian)

### Setup Lingkungan Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

---

## 3. Kompilasi & Build Go TUI

### Build Lokal (Sesuai OS Saat Ini)
Kompilasi kode Go ke dalam biner bbernama `ak` di direktori root untuk pengujian cepat:
```bash
go build -o ak .
./ak
```

### Kompilasi Silang (Cross-Compile) untuk Semua Platform
Untuk membagikan rilis autokeren ke platform lain (Linux, Windows, macOS), jalankan perintah kompilasi silang berikut. Hasil biner akan disimpan di direktori `autokeren/bin/`:

```bash
# 1. Linux AMD64 (64-bit)
GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o autokeren/bin/ak-linux-amd64 .

# 2. Linux ARM64 (e.g. Raspberry Pi)
GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o autokeren/bin/ak-linux-arm64 .

# 3. Windows AMD64 (Windows 64-bit)
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o autokeren/bin/ak-windows-amd64.exe .

# 4. macOS Intel (AMD64)
GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w" -o autokeren/bin/ak-darwin-amd64 .

# 5. macOS Apple Silicon (ARM64 M1/M2/M3)
GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w" -o autokeren/bin/ak-darwin-arm64 .
```
> [!NOTE]
> Parameter `-ldflags="-s -w"` membuang informasi debug dan tabel simbol dari biner, sehingga memperkecil ukuran file biner secara signifikan (menghemat ~30-40% ukuran file).

---

## 4. Pengujian & Kualitas Kode (Python Daemon)
Sebelum melakukan rilis, pastikan kode Python bebas dari error dengan menjalankan tiga pengujian wajib berikut:

```bash
# 1. Jalankan linting dan autofix
ruff check . --fix

# 2. Lakukan pengecekan tipe statis (strict type-safe)
mypy autokeren

# 3. Jalankan seluruh unit tests
PYTHONPATH=. pytest
```

---

## 5. Alur Rilis & Deploy Versi Baru (Semua Platform)
Proyek ini dilengkapi dengan skrip otomatisasi rilis [`./scripts/release.sh`](file:///data/media_backup/autokeren/scripts/release.sh). Skrip ini otomatis:
1.  Melakukan validasi kebersihan git working tree.
2.  Menaikkan (*bump*) nomor versi di `autokeren/__init__.py` dan `pyproject.toml`.
3.  Memasukkan entri fitur baru ke `CHANGELOG.md`.
4.  Menjalankan `ruff` dan `mypy` untuk verifikasi keselamatan.
5.  Melakukan git commit dan git tag (misalnya `v0.11.8`).
6.  Meminta konfirmasi untuk push ke GitHub yang secara otomatis men-trigger CI/CD (GitHub Actions) untuk build build global.

### Cara Penggunaan Skrip Rilis

```bash
# Bump Patch Version (contoh: 0.11.7 → 0.11.8)
./scripts/release.sh patch "menambahkan penyimpanan metadata proyek di SQLite"

# Bump Minor Version (contoh: 0.11.7 → 0.12.0)
./scripts/release.sh minor "pembaruan besar pada arsitektur multi-agent"

# Bump Versi Eksplisit Kustom
./scripts/release.sh 1.0.0 "rilis versi stabil pertama"
```

Setelah skrip rilis selesai dijalankan, Anda dapat mendorong (*push*) perubahan ke server:
```bash
git push origin main && git push origin v0.11.8
```

---

## 6. Cara Memperbarui Secara Global
Setelah rilis baru sukses dideploy dan didistribusikan melalui PyPI/pipx, pengguna dapat memperbarui autokeren mereka dengan:
```bash
pipx upgrade autokeren
```
