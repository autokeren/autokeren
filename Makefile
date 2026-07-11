.PHONY: build test test-py lint-py clean help

# Target default: kompilasi biner Go
build:
	@echo "Mengompilasi Go CLI Driver..."
	go build -o ak main.go
	@echo "Kompilasi selesai. Jalankan './ak' untuk memulai."

# Jalankan semua test suite (Go & Python)
test: test-py
	@echo "Menjalankan Go unit tests..."
	go test -v ./...

# Jalankan test suite Python
test-py:
	@echo "Menjalankan Python unit tests (pytest)..."
	PYTHONPATH=. pytest

# Jalankan linter Python (ruff & mypy)
lint-py:
	@echo "Menjalankan Ruff check..."
	ruff check .
	@echo "Menjalankan Mypy type-safety checks..."
	mypy autokeren

# Bersihkan artifact hasil build
clean:
	@echo "Membersihkan berkas biner..."
	rm -f ak autokeren-cli
	@echo "Pembersihan selesai."

# Tampilkan menu bantuan perintah
help:
	@echo "autokeren Hybrid Architecture Makefile"
	@echo "Perintah yang tersedia:"
	@echo "  make build    : Mengompilasi kode Go menjadi biner 'ak'"
	@echo "  make test     : Menjalankan test suite Go dan Python"
	@echo "  make test-py  : Menjalankan unit test pytest untuk Python"
	@echo "  make lint-py  : Menjalankan ruff check dan mypy untuk Python"
	@echo "  make clean    : Menghapus biner hasil kompilasi"
