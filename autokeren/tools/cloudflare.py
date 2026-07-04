"""Cloudflare deployment tools."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from autokeren.tools.base import Tool, ToolResult


class CloudflareDeployTool(Tool):
    name = "cf_deploy"
    description = "Deploy to Cloudflare Pages or Workers."
    parameters = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "enum": ["pages", "worker"], "description": "Deploy target."},
            "path": {"type": "string", "description": "Project directory.", "default": "."},
            "project_name": {"type": "string", "description": "Cloudflare Pages project name."},
            "worker_name": {"type": "string", "description": "Worker script name or wrangler.toml path."},
        },
        "required": ["target"],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, target: str, path: str = ".", project_name: str | None = None, worker_name: str | None = None, **_) -> ToolResult:
        wrangler = shutil.which("wrangler") or "wrangler"
        cwd = self.project_root / path
        try:
            if target == "pages":
                if not project_name:
                    return ToolResult(error="project_name required for Pages deploy", ok=False)
                cmd = [wrangler, "pages", "deploy", "--project-name", project_name]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=300)
                return ToolResult(output=result.stdout, error=result.stderr or None, ok=result.returncode == 0)
            if target == "worker":
                cmd = [wrangler, "deploy"]
                if worker_name:
                    # If worker_name looks like a file and exists, we trust wrangler to use it via config
                    pass
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=300)
                return ToolResult(output=result.stdout, error=result.stderr or None, ok=result.returncode == 0)
            return ToolResult(error=f"unknown target: {target}", ok=False)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)


class CloudflareBuildTool(Tool):
    name = "cf_build_next"
    description = "Build a Next.js app with @cloudflare/next-on-pages."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Next.js project root.", "default": "."},
            "package_manager": {"type": "string", "enum": ["npm", "pnpm", "yarn"], "default": "npm"},
        },
        "required": [],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, path: str = ".", package_manager: str = "npm", **_) -> ToolResult:
        cwd = self.project_root / path
        try:
            result = subprocess.run(
                [package_manager, "run", "pages:build"],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=300,
            )
            return ToolResult(output=result.stdout, error=result.stderr or None, ok=result.returncode == 0)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)
