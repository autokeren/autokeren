"""Unit tests for the SystemObserver background daemon and self-healing triggers."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from autokeren.daemon import SystemObserver, JSONRPCDaemon


def test_system_observer_files_and_logs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create mock code and log files
        py_file = root / "app.py"
        py_file.write_text("print('hello')", encoding="utf-8")
        
        log_file = root / "error.log"
        log_file.write_text("start server\n", encoding="utf-8")
        
        # Setup mock daemon
        mock_daemon = MagicMock(spec=JSONRPCDaemon)
        
        observer = SystemObserver(str(root), mock_daemon)
        
        # Verify files are tracked
        assert py_file in observer.last_mtimes
        assert log_file in observer.log_files
        assert observer.log_file_pointers[log_file] == log_file.stat().st_size
        
        # 1. Test detection of deleted important file
        py_file.unlink()
        observer._check_file_modifications()
        mock_daemon.trigger_auto_diagnose.assert_called_once_with(
            "File penting terhapus: app.py",
            context=f"Lokasi file yang hilang: {py_file}"
        )
        
        # Reset mock
        mock_daemon.reset_mock()
        
        # 2. Test log tailing & critical error detection
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("Ditemukan fatal error: server crashed!\n")
            
        observer._check_logs()
        mock_daemon.trigger_auto_diagnose.assert_called_once()
        args, kwargs = mock_daemon.trigger_auto_diagnose.call_args
        assert "Ditemukan error kritis di file log: error.log" in args[0]
        assert "fatal error: server crashed!" in kwargs["context"]
