from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from autokeren.tools.base import Tool, ToolResult


class ProofTool(Tool):
    name = "proof"
    description = (
        "Kelola bukti rilis proyek (acceptance criteria, evidence, dan keputusan SHIP/BLOCKED/NEEDS_HUMAN_REVIEW)"
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["plan", "record", "report", "list"],
                "description": "Aksi bukti yang ingin dilakukan: plan, record, report, list",
            },
            "proof_id": {
                "type": "string",
                "description": "ID bukti run (misal: proof-20260717T120000Z)",
            },
            "title": {
                "type": "string",
                "description": "Judul rencana bukti rilis",
            },
            "criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Daftar kriteria penerimaan yang akan diverifikasi",
            },
            "criterion_num": {
                "type": "integer",
                "description": "Nomor kriteria (1-indexed) yang ingin diperbarui",
            },
            "status": {
                "type": "string",
                "enum": ["pending", "passed", "failed", "blocked", "manual_review"],
                "description": "Status kriteria",
            },
            "evidence": {
                "type": "string",
                "description": "Deskripsi atau log bukti empiris hasil pengujian",
            },
        },
        "required": ["action"],
    }

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.proofs_dir = self.project_root / ".autokeren" / "proofs"
        self.proofs_dir.mkdir(parents=True, exist_ok=True)

    def _get_git_sha(self) -> str | None:
        try:
            r = subprocess.run(
                ["git", "-C", str(self.project_root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0:
                return r.stdout.strip()
        except Exception:
            pass
        return None

    def _get_verdict(self, criteria: list[dict[str, Any]]) -> str:
        statuses = [c.get("status", "pending") for c in criteria]
        if any(s in ("failed", "blocked") for s in statuses):
            return "BLOCKED"
        if any(s == "manual_review" for s in statuses):
            return "NEEDS_HUMAN_REVIEW"
        if all(s == "passed" for s in statuses) and statuses:
            return "SHIP"
        return "IN_PROGRESS"

    def _format_verdict_style(self, verdict: str) -> tuple[str, str]:
        if verdict == "SHIP":
            return "[bold green]SHIP[/bold green]", "green"
        if verdict == "BLOCKED":
            return "[bold red]BLOCKED[/bold red]", "red"
        if verdict == "NEEDS_HUMAN_REVIEW":
            return "[bold yellow]NEEDS_HUMAN_REVIEW[/bold yellow]", "yellow"
        return "[bold blue]IN_PROGRESS[/bold blue]", "blue"

    def run(
        self,
        action: str,
        proof_id: str | None = None,
        title: str | None = None,
        criteria: list[str] | None = None,
        criterion_num: int | None = None,
        status: str | None = None,
        evidence: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        if action == "plan":
            if not title or not criteria:
                return ToolResult(error="Aksi 'plan' membutuhkan parameter 'title' dan 'criteria'.", ok=False)
            import uuid
            pid = f"proof-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
            sha = self._get_git_sha()
            payload = {
                "id": pid,
                "title": title,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_commit": sha,
                "criteria": [
                    {"text": text, "status": "pending", "evidence": "", "verified_at": None} for text in criteria
                ],
            }
            file_path = self.proofs_dir / f"{pid}.json"
            try:
                file_path.write_text(json.dumps(payload, indent=2))
            except Exception as e:
                return ToolResult(error=f"Gagal menulis file proof: {e}", ok=False)

            msg = f"Rencana bukti rilis '{title}' berhasil dibuat dengan ID: {pid}"
            return ToolResult(output={"proof_id": pid, "message": msg}, ok=True)

        elif action == "record":
            if not proof_id or criterion_num is None or not status:
                return ToolResult(
                    error="Aksi 'record' membutuhkan parameter 'proof_id', 'criterion_num', dan 'status'.",
                    ok=False,
                )
            file_path = self.proofs_dir / f"{proof_id}.json"
            if not file_path.exists():
                return ToolResult(error=f"Rencana bukti dengan ID '{proof_id}' tidak ditemukan.", ok=False)

            try:
                data = json.loads(file_path.read_text())
            except Exception as e:
                return ToolResult(error=f"Gagal membaca file proof: {e}", ok=False)

            items = data.get("criteria", [])
            idx = criterion_num - 1
            if idx < 0 or idx >= len(items):
                return ToolResult(error=f"Nomor kriteria {criterion_num} di luar jangkauan (1-{len(items)}).", ok=False)

            items[idx]["status"] = status
            items[idx]["evidence"] = evidence or ""
            items[idx]["verified_at"] = datetime.now(timezone.utc).isoformat()
            data["criteria"] = items

            try:
                file_path.write_text(json.dumps(data, indent=2))
            except Exception as e:
                return ToolResult(error=f"Gagal memperbarui file proof: {e}", ok=False)

            verdict = self._get_verdict(items)
            msg = f"Kriteria {criterion_num} berhasil diperbarui menjadi '{status}'. Verdict saat ini: {verdict}"
            return ToolResult(output={"proof_id": proof_id, "verdict": verdict, "message": msg}, ok=True)

        elif action == "report":
            if not proof_id:
                return ToolResult(error="Aksi 'report' membutuhkan parameter 'proof_id'.", ok=False)
            file_path = self.proofs_dir / f"{proof_id}.json"
            if not file_path.exists():
                return ToolResult(error=f"Rencana bukti dengan ID '{proof_id}' tidak ditemukan.", ok=False)

            try:
                data = json.loads(file_path.read_text())
            except Exception as e:
                return ToolResult(error=f"Gagal membaca file proof: {e}", ok=False)

            items = data.get("criteria", [])
            verdict = self._get_verdict(items)
            verdict_formatted, color = self._format_verdict_style(verdict)

            title_text = f"AUTOKEREN PROOF — {verdict_formatted}"
            panel_body = f"[bold]{data.get('title')}[/bold]\n"
            panel_body += f"[dim]ID: {data.get('id')} | Commit: {data.get('source_commit') or 'none'}[/dim]\n\n"

            for i, c in enumerate(items):
                st = c.get("status", "pending")
                icon = "✓" if st == "passed" else "✗" if st in ("failed", "blocked") else "?"
                color_st = "green" if st == "passed" else "red" if st in ("failed", "blocked") else "yellow"
                panel_body += f"[{color_st}]{icon} {i + 1}. {c.get('text')} [{st}][/{color_st}]\n"
                if c.get("evidence"):
                    panel_body += f"   [dim]Evidence: {c.get('evidence')}[/dim]\n"

            console = Console(record=True)
            with console.capture() as capture:
                console.print(Panel(panel_body, title=title_text, border_style=color, expand=False))

            return ToolResult(output=capture.get(), ok=True)

        elif action == "list":
            files = list(self.proofs_dir.glob("*.json"))
            if not files:
                return ToolResult(output="Belum ada rencana bukti rilis yang disimpan.", ok=True)

            table = Table(title="Daftar Rencana Bukti Rilis (Autokeren Proof)")
            table.add_column("No", style="dim")
            table.add_column("Proof ID", style="cyan")
            table.add_column("Judul", style="white")
            table.add_column("Verdict", style="bold")
            table.add_column("Commit", style="dim")

            proof_list = []
            for f in files:
                try:
                    data = json.loads(f.read_text())
                    proof_list.append(data)
                except Exception:
                    pass

            proof_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            for i, p in enumerate(proof_list):
                verdict = self._get_verdict(p.get("criteria", []))
                verdict_fmt, _ = self._format_verdict_style(verdict)
                table.add_row(
                    str(i + 1),
                    p.get("id"),
                    p.get("title"),
                    verdict_fmt,
                    (p.get("source_commit") or "none")[:8],
                )

            console = Console(record=True)
            with console.capture() as capture:
                console.print(table)

            return ToolResult(output=capture.get(), ok=True)

        return ToolResult(error=f"Aksi '{action}' tidak dikenal.", ok=False)
