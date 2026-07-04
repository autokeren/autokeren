# Contributing to autokeren

Terima kasih sudah tertarik berkontribusi ke autokeren. Dokumen ini menjelaskan cara setup environment, code style, dan proses pull request.

## Setup Development Environment

Prasyarat: Python 3.11+ dan git.

```bash
git clone https://github.com/autokeren/autokeren.git
cd autokeren
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Verifikasi instalasi:

```bash
autokeren --help
```

## Code Style

- **ruff** untuk linting dan formatting, dengan `line-length = 120`.
- **mypy** untuk type checking (mode strict dianjurkan).
- Tidak menambahkan komentar kode kecuali diminta.
- UI text dalam Bahasa Indonesia mengikuti konvensi yang sudah ada.

## Linting & Type Checking

Jalankan sebelum commit:

```bash
ruff check .
mypy autokeren
```

## Menjalankan Tests

```bash
pytest
```

Tests harus cepat dan tidak memanggil external API. Gunakan `tmp_path` dan `monkeypatch` untuk isolasi filesystem dan environment.

## Commit Message Convention

Gunakan [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` fitur baru
- `fix:` perbaikan bug
- `docs:` perubahan dokumentasi
- `test:` penambahan/perbaikan test
- `chore:` maintenance, dependency update, config
- `refactor:` refactor tanpa perubahan perilaku

Contoh:

```
feat: tambah tool cf_kv untuk baca/tulis Cloudflare KV
fix: streaming text di dalam Panel bukan plain text
docs: perbarui README dengan commands reference
```

## Pull Request Process

1. Fork repository dan buat branch dari `main` (`feat/nama-fitur` atau `fix/desc-bug`).
2. Pastikan `ruff check .`, `mypy autokeren`, dan `pytest` lolos.
3. Tulis test untuk perubahan baru bila memungkinkan.
4. Update dokumentasi (README, CHANGELOG) bila perilaku pengguna berubah.
5. Buat pull request dengan deskripsi jelas mengenai apa yang diubah dan mengapa.
6. Pastikan CI hijau sebelum review.

## Project Structure

```
autokeren/
├── autokeren/
│   ├── agent.py          # core agentic loop
│   ├── cli.py            # entry point + command parsing
│   ├── config.py         # YAML config loader (pydantic)
│   ├── context.py        # session memory + token tracking
│   ├── memory.py         # cross-session persistent memory
│   ├── prompts.py        # system prompt builder
│   ├── session.py        # save/resume sessions
│   ├── ui.py             # rich terminal UI
│   ├── utils.py          # small helpers
│   ├── models/           # Cloudflare AI client + router + retry
│   └── tools/            # Tool base + registry + 18 tools
├── tests/
├── docs/
│   └── ARCHITECTURE.md
├── pyproject.toml
└── README.md
```

## Pertanyaan?

Buka [issue](https://github.com/autokeren/autokeren/issues) untuk diskusi sebelum mengerjakan fitur besar.
