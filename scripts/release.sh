#!/usr/bin/env bash
#
# release.sh — Bump versi autokeren, update CHANGELOG, commit, tag, push.
#
# Usage:
#   ./scripts/release.sh 0.9.4              # versi eksplisit
#   ./scripts/release.sh patch              # 0.9.3 → 0.9.4
#   ./scripts/release.sh minor              # 0.9.3 → 0.10.0
#   ./scripts/release.sh major              # 0.9.3 → 1.0.0
#   ./scripts/release.sh 0.9.4 "fix: login" # versi + custom changelog
#
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# ── Validasi ──────────────────────────────────────────────────────────
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "❌ Working tree tidak bersih. Commit/stash dulu."
  git status --short
  exit 1
fi

CURRENT=$(grep -oP '(?<=__version__ = ")[^"]+' autokeren/__init__.py)
if [ -z "$CURRENT" ]; then
  echo "❌ Tidak bisa baca versi saat ini dari autokeren/__init__.py"
  exit 1
fi

# ── Hitung versi baru ─────────────────────────────────────────────────
INPUT="${1:-}"
DESC="${2:-}"

if [ -z "$INPUT" ]; then
  echo "Versi sekarang: $CURRENT"
  echo "Usage: $0 <versi|patch|minor|major> [deskripsi changelog]"
  exit 1
fi

case "$INPUT" in
  patch|minor|major)
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
    case "$INPUT" in
      patch) PATCH=$((PATCH + 1)) ;;
      minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
      major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    esac
    NEW_VER="$MAJOR.$MINOR.$PATCH"
    ;;
  *)
    NEW_VER="$INPUT"
    if ! [[ "$NEW_VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "❌ Format versi tidak valid: $NEW_VER (contoh: 0.9.4)"
      exit 1
    fi
    ;;
esac

if [ "$NEW_VER" = "$CURRENT" ]; then
  echo "❌ Versi sama dengan sekarang ($CURRENT). Tidak ada yang diubah."
  exit 1
fi

echo "📦 Bump: $CURRENT → $NEW_VER"

# ── Update file versi ─────────────────────────────────────────────────
sed -i "s/__version__ = \"$CURRENT\"/__version__ = \"$NEW_VER\"/" autokeren/__init__.py
sed -i "s/^version = \"$CURRENT\"/version = \"$NEW_VER\"/" pyproject.toml
sed -i "s/version = \"v$CURRENT\"/version = \"v$NEW_VER\"/" ui/layout.go
sed -i "s/version := \"v$CURRENT\"/version := \"v$NEW_VER\"/" ui/sidebar.go
sed -i "s/const fallbackVersion = \"$CURRENT\"/const fallbackVersion = \"$NEW_VER\"/" cmd/bootstrap.go

# Verifikasi
if ! grep -q "\"$NEW_VER\"" autokeren/__init__.py; then
  echo "❌ Gagal update autokeren/__init__.py"
  exit 1
fi
if ! grep -q "^version = \"$NEW_VER\"" pyproject.toml; then
  echo "❌ Gagal update pyproject.toml"
  exit 1
fi
if ! grep -q "version = \"v$NEW_VER\"" ui/layout.go; then
  echo "❌ Gagal update ui/layout.go"
  exit 1
fi
if ! grep -q "version := \"v$NEW_VER\"" ui/sidebar.go; then
  echo "❌ Gagal update ui/sidebar.go"
  exit 1
fi
if ! grep -q "const fallbackVersion = \"$NEW_VER\"" cmd/bootstrap.go; then
  echo "❌ Gagal update versi runtime Go"
  exit 1
fi

# ── Update CHANGELOG.md ───────────────────────────────────────────────
TODAY=$(date +%Y-%m-%d)
HEADER="## [$NEW_VER] - $TODAY"

if [ -n "$DESC" ]; then
  ENTRY="$HEADER\n\n### Changed\n- $DESC\n"
else
  ENTRY="$HEADER\n\n### Changed\n- Release v$NEW_VER\n"
fi

# Sisipkan setelah baris pertama yang berisi "## [" atau setelah header file
if head -10 CHANGELOG.md | grep -q "^## \["; then
  sed -i "0,/^## \[/{s|^## \[|$ENTRY\n## \[|}" CHANGELOG.md
else
  sed -i "1a\\\n$ENTRY" CHANGELOG.md
fi

echo "✅ CHANGELOG.md diupdate"

# ── Lint & test cepat ─────────────────────────────────────────────────
if [ -x .venv/bin/python ]; then
  PYTHON_BIN=.venv/bin/python
  RUFF_BIN=.venv/bin/ruff
  MYPY_BIN=.venv/bin/mypy
else
  PYTHON_BIN=python3
  RUFF_BIN=ruff
  MYPY_BIN=mypy
fi

echo "🔍 Cek ruff..."
"$RUFF_BIN" check . --quiet || { echo "❌ ruff gagal"; exit 1; }

echo "🔍 Cek mypy..."
"$MYPY_BIN" autokeren || { echo "❌ mypy gagal"; exit 1; }

echo "🔍 Jalankan pytest..."
"$PYTHON_BIN" -m pytest -q || { echo "❌ pytest gagal"; exit 1; }

echo "🔍 Jalankan Go test..."
go test ./... || { echo "❌ Go test gagal"; exit 1; }

echo "🔍 Jalankan Go vet..."
go vet ./... || { echo "❌ Go vet gagal"; exit 1; }

# ── Compile Go prebuilt binaries ─────────────────────────────────────
echo "🔨 Mengompilasi silang biner Go untuk semua platform..."
make build-prebuilt || { echo "❌ Kompilasi Go gagal"; exit 1; }

# ── Commit + tag ──────────────────────────────────────────────────────
git add autokeren/__init__.py pyproject.toml CHANGELOG.md ui/layout.go ui/sidebar.go cmd/bootstrap.go autokeren/bin/

COMMIT_MSG="chore(release): bump version $NEW_VER"
if [ -n "$DESC" ]; then
  COMMIT_MSG="$COMMIT_MSG — $DESC"
fi

git commit -m "$COMMIT_MSG"
git tag "v$NEW_VER"

echo ""
echo "✅ Selesai: v$NEW_VER"
echo "   Commit: $(git rev-parse --short HEAD)"
echo "   Tag:    v$NEW_VER"
echo ""
echo "🚀 Push ke remote untuk trigger CI/CD:"
echo "   git push origin main && git push origin v$NEW_VER"
echo ""
read -rp "Push sekarang? [Y/n] " yn
yn=${yn:-y}
case "$yn" in
  [Yy]*)
    git push origin main
    git push origin "v$NEW_VER"
    echo "✅ Pushed! Cek: https://github.com/autokeren/autokeren/actions"
    ;;
  *)
    echo "⏸️  Dibatalkan. Push manual saat siap."
    ;;
esac
