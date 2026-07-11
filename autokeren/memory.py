"""Memory manager — per-project persistent memory across sessions."""
from __future__ import annotations

import hashlib
import math
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path

from autokeren.utils import now_iso, sanitize_filename

_MAX_MEMORY_LINES = 200


def _project_slug(project_root: str) -> str:
    name = Path(project_root).name or "default"
    h = hashlib.md5(str(Path(project_root).resolve()).encode()).hexdigest()[:8]
    return f"{sanitize_filename(name)}-{h}"


def _config_base() -> Path:
    return Path(os.environ.get("AUTOKEREN_CONFIG_DIR", Path.home() / ".config" / "autokeren"))


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def compute_tfidf_similarity(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    query_tokens = tokenize(query)
    if not query_tokens:
        return [0.0] * len(documents)

    doc_tokens = [tokenize(doc) for doc in documents]
    
    # Vocabulary
    vocab = set(query_tokens)
    for doc in doc_tokens:
        vocab.update(doc)
    vocab_list = list(vocab)
    vocab_idx = {word: i for i, word in enumerate(vocab_list)}
    
    # Document frequency
    df: Counter[str] = Counter()
    for doc in doc_tokens:
        unique_words = set(doc)
        for word in unique_words:
            df[word] += 1
            
    num_docs = len(documents)
    idf = {}
    for word in vocab_list:
        # idf with smoothing
        idf[word] = math.log((1 + num_docs) / (1 + df[word])) + 1
        
    # Query vector
    query_tf = Counter(query_tokens)
    query_vec = [0.0] * len(vocab_list)
    for word, tf in query_tf.items():
        if word in vocab_idx:
            query_vec[vocab_idx[word]] = tf * idf[word]
            
    # Doc vectors
    doc_vecs = []
    for doc in doc_tokens:
        doc_tf = Counter(doc)
        doc_vec = [0.0] * len(vocab_list)
        for word, tf in doc_tf.items():
            if word in vocab_idx:
                doc_vec[vocab_idx[word]] = tf * idf[word]
        doc_vecs.append(doc_vec)
        
    # Cosine similarity
    similarities = []
    query_norm = math.sqrt(sum(val * val for val in query_vec))
    if query_norm == 0:
        return [0.0] * len(documents)
        
    for doc_vec in doc_vecs:
        doc_norm = math.sqrt(sum(val * val for val in doc_vec))
        if doc_norm == 0:
            similarities.append(0.0)
            continue
        dot_product = sum(q * d for q, d in zip(query_vec, doc_vec))
        similarities.append(dot_product / (query_norm * doc_norm))
        
    return similarities


class MemoryManager:
    """Kelola memory.md (markdown) & memory.db (SQLite) per project.
    
    Disimpan di ~/.config/autokeren/projects/<slug>/.
    Menyediakan pencarian semantik (TF-IDF VSM) secara lokal.
    """

    def __init__(self, project_root: str, max_lines: int = _MAX_MEMORY_LINES):
        self.project_root = project_root
        self.max_lines = max_lines
        self.project_dir = _config_base() / "projects" / _project_slug(project_root)
        self.memory_file = self.project_dir / "memory.md"
        self.db_file = self.project_dir / "memory.db"
        self._init_db()

    def _init_db(self) -> None:
        self.project_dir.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT,
                    task_title TEXT,
                    lesson TEXT,
                    success INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def log_message(self, session_id: str, role: str, content: str) -> None:
        """Simpan transkrip pesan ke database SQLite."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute(
                    "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                    (session_id, role, content),
                )
        except Exception:
            pass

    def search_relevant(self, query: str, limit: int = 5) -> list[str]:
        """Lakukan pencarian semantik (TF-IDF VSM) di markdown & SQLite lessons."""
        documents: list[str] = []
        
        # 1. Baca dari memory.md (menangkap manual edits oleh user)
        if self.memory_file.exists():
            try:
                content = self.memory_file.read_text(encoding="utf-8", errors="replace")
                # Ambil semua bullet points di memory.md
                for line in content.splitlines():
                    clean_line = line.strip()
                    if clean_line.startswith("- "):
                        note = clean_line[2:].strip()
                        if note and note not in documents:
                            documents.append(note)
            except Exception:
                pass

        # 2. Baca dari SQLite lessons table
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.execute("SELECT pattern, task_title, lesson FROM lessons")
                for row in cursor.fetchall():
                    pattern, title, lesson = row
                    note = f"[{pattern}] {title}: {lesson}"
                    if note not in documents:
                        documents.append(note)
        except Exception:
            pass

        if not documents:
            return []

        # 3. Hitung TF-IDF Similarity
        try:
            sims = compute_tfidf_similarity(query, documents)
            # Gabungkan dan urutkan
            scored_docs = sorted(zip(sims, documents), key=lambda x: x[0], reverse=True)
            # Ambil yang skor > 0 (relevan)
            relevant_docs = [doc for score, doc in scored_docs if score > 0.05]
            return relevant_docs[:limit]
        except Exception:
            return documents[:limit]

    def load(self) -> str:
        """Load memory content (max max_lines baris)."""
        if not self.memory_file.exists() or self.memory_file.stat().st_size == 0:
            self._initialize_default_memory()
        lines = self.memory_file.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[: self.max_lines])

    def _initialize_default_memory(self) -> None:
        """Inisialisasi file memory.md default dengan metadata proyek."""
        path = Path(self.project_root).resolve()
        name = path.name or "default"
        
        # Tebak tech stack
        stacks = []
        if (path / "package.json").exists():
            stacks.append("Node.js")
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists() or (path / "setup.py").exists():
            stacks.append("Python")
        if (path / "go.mod").exists():
            stacks.append("Go")
        if (path / "Cargo.toml").exists():
            stacks.append("Rust")
        if (path / "wrangler.toml").exists() or (path / "wrangler.json").exists():
            stacks.append("Cloudflare Workers")
        tech_stack = ", ".join(stacks) if stacks else "Unknown"

        template = (
            f"# Project Memory: {name}\n\n"
            f"## Metadata Proyek\n"
            f"- **Nama Project**: {name}\n"
            f"- **Direktori**: {path}\n"
            f"- **Teknologi**: {tech_stack}\n"
            f"- **Link Frontend (FE)**: (Silakan diisi, contoh: http://localhost:3000)\n"
            f"- **Link Backend (BE)**: (Silakan diisi, contoh: http://localhost:8787)\n\n"
            f"## Panduan / Runbook\n"
            f"- **Install Dependencies**: (contoh: npm install atau pip install)\n"
            f"- **Jalankan Aplikasi**: (contoh: npm run dev)\n"
            f"- **Jalankan Pengujian**: (contoh: pytest atau npm test)\n\n"
            f"## Catatan Kunci & Context\n"
            f"- Proyek ini dikelola menggunakan autokeren CLI.\n"
        )
        self.save(template)

    def save(self, content: str) -> None:
        """Overwrite memory file."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(content, encoding="utf-8")

    def append(self, section: str, note: str) -> str:
        """Append note ke section tertentu. Buat section kalau belum ada."""
        existing = ""
        if self.memory_file.exists():
            existing = self.memory_file.read_text(encoding="utf-8", errors="replace")

        header = f"## {section}"
        if header in existing:
            existing = existing.replace(header + "\n", header + f"\n- {note}\n")
        else:
            ts = now_iso()[:10]
            if existing and not existing.endswith("\n"):
                existing += "\n"
            existing += f"\n{header}\n_Update: {ts}_\n- {note}\n"

        self.save(existing)
        
        # Simpan juga ke SQLite lessons table
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute(
                    "INSERT INTO lessons (pattern, task_title, lesson, success) VALUES (?, ?, ?, ?)",
                    (section, "manual_note" if "autoplan" not in section else section, note, 1),
                )
        except Exception:
            pass

        return existing

    def clear(self) -> None:
        """Hapus semua memory."""
        if self.memory_file.exists():
            self.memory_file.write_text("", encoding="utf-8")
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.execute("DELETE FROM messages")
                conn.execute("DELETE FROM lessons")
        except Exception:
            pass

    def get_path(self) -> Path:
        return self.memory_file

    def exists(self) -> bool:
        return self.memory_file.exists()

    def line_count(self) -> int:
        if not self.memory_file.exists():
            return 0
        return len(self.memory_file.read_text(encoding="utf-8", errors="replace").splitlines())
