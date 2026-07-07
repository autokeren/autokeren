"""Tests for Architecture Guardian — genome scanner + checker."""
from __future__ import annotations

from pathlib import Path

from autokeren.genome.scanner import GenomeScanner
from autokeren.genome.checker import GuardianChecker
from autokeren.genome.models import Module, FunctionEntry, ProjectGenome


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project with 2 modules."""
    auth = tmp_path / "auth"
    auth.mkdir()
    (auth / "__init__.py").write_text("")
    (auth / "login.py").write_text(
        "def login(user, password):\n"
        "    return True\n"
        "\n"
        "def logout(session):\n"
        "    pass\n"
    )
    api = tmp_path / "api"
    api.mkdir()
    (api / "__init__.py").write_text("")
    (api / "routes.py").write_text(
        "def get_users():\n"
        "    return []\n"
        "\n"
        "class UserHandler:\n"
        "    pass\n"
    )
    return tmp_path


def test_scanner_detects_modules(tmp_path: Path):
    """Scanner detects modules dari directory structure."""
    _make_project(tmp_path)
    scanner = GenomeScanner(tmp_path)
    genome = scanner.scan()
    names = [m.name for m in genome.modules]
    assert "auth" in names
    assert "api" in names


def test_scanner_detects_language(tmp_path: Path):
    """Scanner detects Python language dari .py files."""
    _make_project(tmp_path)
    scanner = GenomeScanner(tmp_path)
    genome = scanner.scan()
    for m in genome.modules:
        assert m.language == "python"


def test_scanner_indexes_functions(tmp_path: Path):
    """Scanner indexes function names untuk duplicate detection."""
    _make_project(tmp_path)
    scanner = GenomeScanner(tmp_path)
    genome = scanner.scan()
    assert "login" in genome.function_index
    assert "logout" in genome.function_index
    assert "get_users" in genome.function_index
    assert "UserHandler" in genome.function_index


def test_guardian_block_duplicate_function(tmp_path: Path):
    """Agent coba bikin function yang sudah ada di module lain → BLOCKED."""
    _make_project(tmp_path)
    scanner = GenomeScanner(tmp_path)
    genome = scanner.scan()
    checker = GuardianChecker(genome, block_duplicates=True)
    new_content = "def login(user, password):\n    return False\n"
    result = checker.check_before_write("newauth/handler.py", new_content)
    assert result.blocked
    assert "login" in result.reason


def test_guardian_allow_unique_function(tmp_path: Path):
    """Agent bikin function baru yang belum ada → ALLOWED."""
    _make_project(tmp_path)
    scanner = GenomeScanner(tmp_path)
    genome = scanner.scan()
    checker = GuardianChecker(genome, block_duplicates=True)
    new_content = "def register(user, email):\n    return True\n"
    result = checker.check_before_write("auth/register.py", new_content)
    assert not result.blocked


def test_guardian_allow_extend_existing_module(tmp_path: Path):
    """Agent tambah file di module yang sudah ada → ALLOWED."""
    _make_project(tmp_path)
    scanner = GenomeScanner(tmp_path)
    genome = scanner.scan()
    checker = GuardianChecker(genome, block_duplicates=True)
    new_content = "def refresh_token(session):\n    return 'new_token'\n"
    result = checker.check_before_write("auth/tokens.py", new_content)
    assert not result.blocked


def test_genome_empty_project(tmp_path: Path):
    """Empty project → genome kosong, guardian ga block apapun."""
    scanner = GenomeScanner(tmp_path)
    genome = scanner.scan()
    checker = GuardianChecker(genome, block_duplicates=True)
    result = checker.check_before_write("anything.py", "def foo():\n    pass\n")
    assert not result.blocked


def test_genome_find_duplicate_functions(tmp_path: Path):
    """find_duplicate_functions detects same name across modules."""
    genome = ProjectGenome(root=".")
    genome.function_index = {
        "login": [
            FunctionEntry(name="login", module="auth", file="auth/login.py", line=1),
            FunctionEntry(name="login", module="api", file="api/auth.py", line=5),
        ],
        "logout": [
            FunctionEntry(name="logout", module="auth", file="auth/login.py", line=5),
        ],
    }
    dups = genome.find_duplicate_functions()
    assert "login" in dups
    assert "logout" not in dups
    assert len(dups["login"]) == 2


def test_genome_to_markdown(tmp_path: Path):
    """Genome generates markdown output."""
    genome = ProjectGenome(root=".", last_updated="2026-01-01T00:00:00Z")
    genome.modules.append(Module(name="auth", path="auth", language="python", key_files=["auth/login.py"]))
    md = genome.to_markdown()
    assert "Project Genome" in md
    assert "auth" in md
    assert "python" in md
