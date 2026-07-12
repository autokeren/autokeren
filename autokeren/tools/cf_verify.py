"""Pillar C: Visual E2E Verification Tool menggunakan Go-Rod via IPC."""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from autokeren.tools.base import Tool, ToolResult


@dataclass
class _VerifyReport:
    url: str
    timestamp: str = field(default_factory=lambda: time.strftime("%Y%m%dT%H%M%S"))
    http_status: int | None = None
    screenshot_path: str | None = None
    assertions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    ok: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "timestamp": self.timestamp,
            "http_status": self.http_status,
            "screenshot_path": self.screenshot_path,
            "assertions": self.assertions,
            "errors": self.errors,
            "ok": self.ok,
        }


class CfVerifyTool(Tool):
    name = "cf_verify"
    description = (
        "Verifikasi visual E2E setelah deployment ke Cloudflare Pages/Workers. "
        "Buka URL di headless browser (Go-Rod), ambil screenshot, cek HTTP status, "
        "dan simpan hasilnya ke .ak-verification/. "
        "Gunakan setelah deploy berhasil untuk memastikan halaman tidak crash."
    )
    requires_permission = False
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL yang akan diverifikasi (misal: https://my-app.pages.dev)",
            },
            "assert_text": {
                "type": "string",
                "description": "Teks yang harus tampil di halaman (opsional).",
            },
            "assert_selector": {
                "type": "string",
                "description": "CSS selector yang harus ada di halaman (opsional).",
            },
            "wait_seconds": {
                "type": "number",
                "description": "Waktu tunggu setelah navigasi sebelum screenshot (default: 3).",
            },
        },
        "required": ["url"],
    }

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root)

    def run(
        self,
        url: str,
        assert_text: str = "",
        assert_selector: str = "",
        wait_seconds: float = 3.0,
        **_: object,
    ) -> ToolResult:
        verify_dir = self.project_root / ".ak-verification"
        verify_dir.mkdir(parents=True, exist_ok=True)

        report = _VerifyReport(url=url)

        # 1. HTTP status check
        try:
            r = httpx.get(url, follow_redirects=True, timeout=15.0)
            report.http_status = r.status_code
            if r.status_code >= 400:
                report.errors.append(f"HTTP {r.status_code} — halaman error")
        except Exception as e:
            report.errors.append(f"HTTP check gagal: {e}")
            self._save_report(verify_dir, report)
            return ToolResult(error=f"HTTP check gagal: {e}", ok=False)

        # 2. Headless browser via IPC (jika daemon aktif)
        self._browser_verify(url, assert_text, assert_selector, wait_seconds, verify_dir, report)

        # 3. Simpan report JSON
        report_path = self._save_report(verify_dir, report)

        if report.errors:
            errors_str = "; ".join(report.errors)
            return ToolResult(
                output=json.dumps(report.to_dict(), indent=2),
                error=f"Verifikasi selesai dengan {len(report.errors)} masalah: {errors_str}",
                ok=False,
            )

        lines = [
            f"✅ Verifikasi {url} PASSED",
            f"   HTTP status : {report.http_status}",
            f"   Screenshot  : {report.screenshot_path or 'N/A'}",
            f"   Report      : {report_path}",
        ]
        for a in report.assertions:
            lines.append(f"   Assert      : {a}")
        report.ok = True
        self._save_report(verify_dir, report)
        return ToolResult(output="\n".join(lines), ok=True)

    def _browser_verify(
        self,
        url: str,
        assert_text: str,
        assert_selector: str,
        wait_seconds: float,
        verify_dir: Path,
        report: _VerifyReport,
    ) -> None:
        try:
            from autokeren import daemon as _daemon  # noqa: F401
            send_fn = getattr(_daemon, "send_ipc_request", None)
            if send_fn is None:
                raise ImportError("send_ipc_request not found")
        except ImportError:
            report.errors.append("IPC daemon tidak aktif, skip headless check")
            return

        try:
            send_fn("ui.control_browser", {"action": "navigate", "args": {"url": url}})
            time.sleep(wait_seconds)

            ss_result: dict[str, object] = send_fn(
                "ui.control_browser", {"action": "screenshot", "args": {}}
            ) or {}
            if ss_result.get("ok"):
                output = ss_result.get("output")
                if isinstance(output, dict):
                    b64 = str(output.get("base64", ""))
                    if b64:
                        safe_host = url.replace("https://", "").replace("http://", "").replace("/", "_")[:40]
                        ss_path = verify_dir / f"{report.timestamp}_{safe_host}.png"
                        ss_path.write_bytes(base64.b64decode(b64))
                        report.screenshot_path = str(ss_path)

            if assert_text:
                res: dict[str, object] = send_fn(
                    "ui.control_browser",
                    {"action": "assert", "args": {"assertion": {"kind": "visible_text", "value": assert_text}}},
                ) or {}
                output_res = res.get("output")
                ok = bool(isinstance(output_res, dict) and output_res.get("ok"))
                status = "✅ PASS" if ok else "❌ FAIL"
                report.assertions.append(f"{status} visible_text: '{assert_text}'")
                if not ok:
                    report.errors.append(f"Teks '{assert_text}' tidak ditemukan")

            if assert_selector:
                res2: dict[str, object] = send_fn(
                    "ui.control_browser",
                    {"action": "assert", "args": {"assertion": {"kind": "selector", "value": assert_selector}}},
                ) or {}
                output_res2 = res2.get("output")
                ok2 = bool(isinstance(output_res2, dict) and output_res2.get("ok"))
                status2 = "✅ PASS" if ok2 else "❌ FAIL"
                report.assertions.append(f"{status2} selector: '{assert_selector}'")
                if not ok2:
                    report.errors.append(f"Selector '{assert_selector}' tidak ditemukan")

        except Exception as e:
            report.errors.append(f"Browser error: {e}")

    def _save_report(self, verify_dir: Path, report: _VerifyReport) -> Path:
        report_path = verify_dir / f"report_{report.timestamp}.json"
        report_path.write_text(json.dumps(report.to_dict(), indent=2, default=str))
        return report_path
