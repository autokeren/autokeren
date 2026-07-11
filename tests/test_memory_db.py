"""Unit tests for SQLite logging and TF-IDF semantic search memory manager."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from autokeren.memory import MemoryManager


def test_memory_db_logging_and_search() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        
        # Initialize MemoryManager
        memory = MemoryManager(str(project_root))
        memory.load()
        
        # Check files are created
        assert memory.memory_file.exists()
        assert memory.db_file.exists()
        
        # Test DB tables are present
        with sqlite3.connect(memory.db_file) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "messages" in tables
            assert "lessons" in tables
            
        # Test logging message
        memory.log_message(session_id="session1", role="user", content="kopi juara adalah kedai kopi hebat")
        memory.log_message(session_id="session1", role="assistant", content="terima kasih atas masukannya")
        
        with sqlite3.connect(memory.db_file) as conn:
            cursor = conn.execute("SELECT role, content FROM messages")
            rows = cursor.fetchall()
            assert len(rows) == 2
            assert rows[0] == ("user", "kopi juara adalah kedai kopi hebat")
            
        # Test appending structured notes (syncs to lessons table)
        memory.append("preferensi", "User menyukai kopi espresso robusta")
        memory.append("build", "Jalankan npm run dev untuk start server")
        
        with sqlite3.connect(memory.db_file) as conn:
            cursor = conn.execute("SELECT pattern, lesson FROM lessons")
            lessons = cursor.fetchall()
            assert len(lessons) == 2
            assert lessons[0] == ("preferensi", "User menyukai kopi espresso robusta")
            
        # Test semantic RAG TF-IDF search
        # 1. Search "espresso"
        results_espresso = memory.search_relevant("Saya ingin espresso", limit=2)
        assert len(results_espresso) >= 1
        assert "espresso" in results_espresso[0]
        
        # 2. Search "server"
        results_server = memory.search_relevant("Bagaimana cara jalankan server?", limit=2)
        assert len(results_server) >= 1
        assert "npm run dev" in results_server[0]
        
        # 3. Search non-relevant query
        results_none = memory.search_relevant("kursi meja kayu", limit=2)
        assert len(results_none) == 0
