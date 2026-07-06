"""autokeren.multiagent.tdd — Engine TDD (Red-Green-Refactor) Multi-Agent."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable

from autokeren.agent import Agent


class TDDEngine:
    """Engine yang mengatur alur TDD otomatis menggunakan model AI."""

    def __init__(self, agent: Agent, project_root: str, log_fn: Callable[[str], None]) -> None:
        self.agent = agent
        self.project_root = Path(project_root)
        self.log = log_fn

    def detect_environment(self) -> dict[str, str]:
        """Deteksi otomatis bahasa dan test runner yang digunakan di workspace."""
        if (self.project_root / "package.json").exists():
            return {
                "lang": "JavaScript/TypeScript",
                "test_runner": "npm test",
                "test_ext": ".test.js",
                "code_ext": ".js",
                "test_dir": "tests",
            }
        # Default ke Python/Pytest
        return {
            "lang": "Python",
            "test_runner": ".venv/bin/pytest" if (self.project_root / ".venv").exists() else "pytest",
            "test_ext": "_test.py",
            "code_ext": ".py",
            "test_dir": "tests",
        }

    def _extract_code(self, text: str) -> str:
        """Ekstrak blok kode markdown dari jawaban AI."""
        match = re.search(r"```[a-zA-Z0-9]*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def run_tests(self, runner_cmd: str, target_test_path: Path) -> tuple[bool, str]:
        """Jalankan unit test dan kembalikan status sukses beserta output log."""
        try:
            # Jalankan test runner pada file spesifik
            res = subprocess.run(
                f"{runner_cmd} {target_test_path}",
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = res.stdout + "\n" + res.stderr
            return (res.returncode == 0, output)
        except subprocess.TimeoutExpired:
            return (False, "Timeout: Eksekusi unit test memakan waktu terlalu lama (>30s).")
        except Exception as exc:
            return (False, f"Error menjalankan test runner: {exc}")

    def execute_tdd_flow(self, task_description: str, target_name: str) -> bool:
        """Menjalankan loop Red-Green-Refactor lengkap."""
        env = self.detect_environment()
        self.log(f"[bold cyan]🔍 Terdeteksi environment: {env['lang']} menggunakan {env['test_runner']}[/bold cyan]\n")

        # Inisialisasi lokasi file
        test_dir = self.project_root / env["test_dir"]
        test_dir.mkdir(exist_ok=True)
        
        # Buat nama file berdasarkan target_name
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "", target_name.lower().replace(" ", "_"))
        
        if env["lang"] == "Python":
            test_file = test_dir / f"test_{clean_name}.py"
            code_file = self.project_root / f"{clean_name}.py"
        else:
            test_file = test_dir / f"{clean_name}{env['test_ext']}"
            code_file = self.project_root / f"{clean_name}{env['code_ext']}"

        self.log(f"📍 [dim]Target Code File: {code_file.relative_to(self.project_root)}[/dim]")
        self.log(f"📍 [dim]Target Test File: {test_file.relative_to(self.project_root)}[/dim]\n")

        # ----------------------------------------------------------------------
        # PHASE 1: RED (Tester Agent) 🔴
        # ----------------------------------------------------------------------
        self.log("[bold red]🔴 PHASE 1: RED (Menulis Unit Test yang Sengaja Gagal)[/bold red]")
        
        red_prompt = (
            f"Kamu adalah RED Agent (Tester QA Profesional). Tugas kamu adalah menulis unit test yang kokoh dalam {env['lang']} "
            f"untuk fitur berikut: '{task_description}'.\n"
            f"Unit test ini HARUS mengimpor fungsi/class dari target file '{clean_name}' (misal: 'from {clean_name} import ...' atau 'const ... = require(\"./{clean_name}\")').\n"
            f"Tulis kode test yang komprehensif, mencakup edge-cases, dan HARUS GAGAL saat dijalankan karena kode implementasinya belum dibuat.\n"
            f"Keluarkan HANYA blok kode test di dalam format markdown ```{env['lang'].lower()} ... ``` tanpa penjelasan teks lain."
        )

        resp = self.agent.router.complete([{"role": "user", "content": red_prompt}], max_tokens=2048)
        test_code = self._extract_code(resp.content or "")
        
        # Tulis test file ke disk
        test_file.write_text(test_code, encoding="utf-8")
        self.log("[dim]✓ Menulis file test baru.[/dim]\n")

        # Pastikan code file kosong dulu agar test gagal
        code_file.write_text("", encoding="utf-8")

        # Jalankan test, verifikasi harus GAGAL
        self.log("🧪 Menjalankan unit test untuk memastikan status RED...")
        ok, log = self.run_tests(env["test_runner"], test_file)
        
        if not ok:
            self.log("[bold green]✓ RED Status Terverifikasi! Unit test gagal secara alami (tidak ada implementasi).[/bold green]\n")
        else:
            self.log("[yellow]⚠ Peringatan: Test langsung lulus/hijau. RED Agent akan menulis ulang test case yang lebih mendalam.[/yellow]")
            # Coba sekali lagi dengan prompt lebih ketat
            resp = self.agent.router.complete([
                {"role": "user", "content": red_prompt + "\nPastikan test kamu menegaskan perilaku yang belum ada sehingga test pasti gagal!"}
            ], max_tokens=2048)
            test_code = self._extract_code(resp.content or "")
            test_file.write_text(test_code, encoding="utf-8")
            ok, log = self.run_tests(env["test_runner"], test_file)
            if ok:
                self.log("[red]✗ Kesalahan: Unit test tetap lulus tanpa kode implementasi. Menghentikan alur TDD.[/red]")
                return False

        # ----------------------------------------------------------------------
        # PHASE 2: GREEN (Coder Agent) 🟢
        # ----------------------------------------------------------------------
        self.log("[bold green]🟢 PHASE 2: GREEN (Menulis Kode Implementasi agar Test Lulus)[/bold green]")
        
        for attempt in range(1, 4):
            self.log(f"Attempt {attempt}/3 untuk meloloskan unit test...")
            blue_prompt = (
                f"Kamu adalah BLUE Agent (Developer Coder Efisien). Tugas kamu adalah menulis kode implementasi minimal dalam {env['lang']} "
                f"untuk meloloskan unit test berikut:\n\n"
                f"```\n{test_code}\n```\n\n"
                f"Error log dari test yang gagal:\n\n"
                f"```\n{log[:1500]}\n```\n\n"
                f"Tulis kode implementasi agar test tersebut LULUS (hijau). Jangan menulis kode test, melainkan kode aplikasi saja.\n"
                f"Keluarkan HANYA blok kode implementasi di dalam format markdown ```{env['lang'].lower()} ... ``` tanpa penjelasan teks lain."
            )
            
            resp = self.agent.router.complete([{"role": "user", "content": blue_prompt}], max_tokens=2048)
            impl_code = self._extract_code(resp.content or "")
            code_file.write_text(impl_code, encoding="utf-8")

            # Jalankan test lagi
            ok, log = self.run_tests(env["test_runner"], test_file)
            if ok:
                self.log("[bold green]✓ GREEN Status Tercapai! Unit test berhasil diloloskan dengan sukses.[/bold green]\n")
                break
            else:
                self.log(f"[yellow]✗ Gagal meloloskan test pada attempt {attempt}. Mencoba memperbaiki...[/yellow]")
        else:
            self.log("[bold red]✗ Gagal mencapai status GREEN setelah 3 kali percobaan.[/bold red]")
            return False

        # ----------------------------------------------------------------------
        # PHASE 3: REFACTOR (Refactor Agent) 🔵
        # ----------------------------------------------------------------------
        self.log("[bold blue]🔵 PHASE 3: REFACTOR (Membersihkan & Merapikan Struktur Kode)[/bold blue]")
        
        refactor_prompt = (
            f"Kamu adalah REFACTOR Agent (Clean Code Architect). Tugas kamu adalah melakukan refactor pada kode implementasi berikut "
            f"agar lebih bersih, modular, mengikuti best practices, tanpa merusak perilaku unit test.\n\n"
            f"Kode implementasi saat ini:\n"
            f"```\n{impl_code}\n```\n\n"
            f"Unit test yang menjaga kode ini:\n"
            f"```\n{test_code}\n```\n\n"
            f"Keluarkan HANYA blok kode implementasi hasil refactor di dalam format markdown ```{env['lang'].lower()} ... ```. "
            f"Jika tidak ada yang perlu direfactor, keluarkan kode yang sama persis."
        )

        resp = self.agent.router.complete([{"role": "user", "content": refactor_prompt}], max_tokens=2048)
        refactored_code = self._extract_code(resp.content or "")
        
        # Tulis kode hasil refactor
        code_file.write_text(refactored_code, encoding="utf-8")

        # Jalankan test terakhir untuk verifikasi akhir
        self.log("🧪 Memverifikasi unit test pasca-refactor...")
        ok, log = self.run_tests(env["test_runner"], test_file)
        
        if ok:
            self.log("[bold green]✓ REFACTOR Sukses! Semua test tetap hijau setelah kode dibersihkan.[/bold green]\n")
            self.log("[bold gold]★ PROSES TDD SELESAI DENGAN SUKSES! ★[/bold gold]")
            return True
        else:
            self.log("[yellow]⚠ Refactor merusak test. Mengembalikan kode ke versi GREEN sebelumnya.[/yellow]")
            code_file.write_text(impl_code, encoding="utf-8")
            return True
