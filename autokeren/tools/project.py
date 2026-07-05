"""Project management tools — create, deploy, list via autokeren platform API."""
from __future__ import annotations

from typing import Any

import httpx

from autokeren.config import Config
from autokeren.tools.base import Tool, ToolResult


def _headers(cfg: Config) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {cfg.auth.api_key}",
        "Content-Type": "application/json",
    }


class CreateProjectTool(Tool):
    name = "create_project"
    description = (
        "Buat project baru di platform autokeren. Auto-provision D1 database + R2 bucket + AI binding. "
        "Return project_id, d1_database_id, r2_bucket, worker_name. "
        "Gunakan ini sebelum deploy_project."
    )
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Nama project (huruf kecil, dash). Contoh: toko-sepatu"},
            "description": {"type": "string", "description": "Deskripsi singkat project.", "default": ""},
        },
        "required": ["name"],
    }

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def run(self, name: str, description: str = "", **_: Any) -> ToolResult:
        try:
            r = httpx.post(
                f"{self.cfg.auth.base_url}/v1/projects",
                headers=_headers(self.cfg),
                json={"name": name, "description": description},
                timeout=30.0,
            )
            data = r.json()
            if r.status_code in (200, 201):
                output = (
                    f"Project created!\n"
                    f"  project_id: {data.get('project_id')}\n"
                    f"  name: {data.get('name')}\n"
                    f"  d1_database_id: {data.get('d1_database_id')}\n"
                    f"  d1_database_name: {data.get('d1_database_name')}\n"
                    f"  r2_bucket: {data.get('r2_bucket')}\n"
                    f"  worker_name: {data.get('worker_name')}\n"
                    f"\nBinding names di Worker code:\n"
                    f"  env.DB — D1 database\n"
                    f"  env.STORAGE — R2 bucket\n"
                    f"  env.AI — Workers AI\n"
                    f"\nSimpan project_id untuk deploy nanti."
                )
                return ToolResult(output=output)
            return ToolResult(error=data.get("error", {}).get("message", str(data)), ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)


class DeployProjectTool(Tool):
    name = "deploy_project"
    description = (
        "Deploy Worker code ke project autokeren. "
        "Worker script akan di-deploy dengan auto-bindings: env.DB (D1), env.STORAGE (R2), env.AI (Workers AI). "
        "Return URL live worker. "
        "Bisa pakai file_path (baca dari file) ATAU script (inline code). Pakai file_path lebih disarankan untuk code panjang."
    )
    requires_permission = True
    parameters = {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project ID dari create_project."},
            "file_path": {"type": "string", "description": "Path ke file Worker JavaScript (baca dari disk). Disarankan pakai ini untuk code panjang."},
            "script": {"type": "string", "description": "Worker JavaScript code inline (untuk code pendek)."},
        },
        "required": ["project_id"],
    }

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def run(self, project_id: str, script: str = "", file_path: str = "", **_: Any) -> ToolResult:
        if file_path:
            from pathlib import Path
            p = Path(file_path)
            if not p.exists():
                return ToolResult(error=f"file not found: {file_path}", ok=False)
            script = p.read_text(encoding="utf-8")
        if not script:
            return ToolResult(error="Either file_path atau script harus diisi.", ok=False)
        try:
            from autokeren.signing import check_signed, sign_content
            if not check_signed(file_path or "worker.js", script):
                script = sign_content(file_path or "worker.js", script)
        except ImportError:
            pass
        try:
            r = httpx.post(
                f"{self.cfg.auth.base_url}/v1/projects/{project_id}/deploy",
                headers=_headers(self.cfg),
                json={"script": script},
                timeout=60.0,
            )
            data = r.json()
            if r.status_code in (200, 201):
                output = (
                    f"Deployed!\n"
                    f"  url: {data.get('url')}\n"
                    f"  worker_name: {data.get('worker_name')}\n"
                    f"  bindings: {', '.join(data.get('bindings', []))}\n"
                    f"  status: {data.get('status')}\n"
                    f"\nWorker live di atas. D1, R2, AI binding otomatis tersambung."
                )
                return ToolResult(output=output)
            return ToolResult(error=data.get("error", {}).get("message", str(data)), ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)


class ListProjectsTool(Tool):
    name = "list_projects"
    description = "List semua project autokeren milik user. Return nama, URL, status."
    parameters = {"type": "object", "properties": {}}

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def run(self, **_: Any) -> ToolResult:
        try:
            r = httpx.get(
                f"{self.cfg.auth.base_url}/v1/projects",
                headers=_headers(self.cfg),
                timeout=15.0,
            )
            data = r.json()
            if r.status_code == 200:
                projects = data.get("projects", [])
                if not projects:
                    return ToolResult(output="Belum ada project. Gunakan create_project untuk buat baru.")
                lines = [f"Found {len(projects)} project(s):\n"]
                for p in projects:
                    lines.append(f"  {p.get('name')} [{p.get('status')}]")
                    lines.append(f"    id: {p.get('id')}")
                    if p.get("worker_url"):
                        lines.append(f"    url: {p.get('worker_url')}")
                    lines.append(f"    created: {p.get('created_at', '')[:19]}")
                    lines.append("")
                return ToolResult(output="\n".join(lines))
            return ToolResult(error=data.get("error", {}).get("message", str(data)), ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)
