"""FDDM Tool — Feromon Digital Distributed Memory integration."""
from __future__ import annotations

from typing import Any

from autokeren.tools.base import Tool, ToolResult


class FDDMTool(Tool):
    name = "fddm"
    description = (
        "Operasi FDDM (Feromon Digital Distributed Memory) — memori kolektif antar agent. "
        "Aksi: emit (simpan memori), sniff (cari memori relevan), stats (lihat statistik), "
        "decay (jalankan pemudaran), trust (lapor kepercayaan emitter). "
        "Hanya aktif jika fddm.enabled=true di config."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["emit", "sniff", "stats", "decay", "trust"],
                "description": "Aksi FDDM yang ingin dilakukan.",
            },
            "type": {
                "type": "string",
                "enum": ["error", "decision", "document", "conversation", "artifact", "observation"],
                "description": "Tipe scent (untuk emit). error=bug/gagal, decision=keputusan, document=dokumen/info, conversation=percakapan, artifact=file, observation=pengamatan.",
            },
            "text": {
                "type": "string",
                "description": "Teks untuk emit atau sniff (auto-embed via Workers AI).",
            },
            "emitter_id": {
                "type": "string",
                "description": "ID agent/emitter yang meng-emit (untuk emit/trust).",
            },
            "top_k": {
                "type": "integer",
                "description": "Jumlah hasil maksimal (untuk sniff). Default 5.",
            },
            "radius": {
                "type": "number",
                "description": "Minimum similarity (0-1) untuk sniff. Default 0.3.",
            },
            "success": {
                "type": "boolean",
                "description": "Apakah emitter berhasil membantu (untuk trust).",
            },
        },
        "required": ["action"],
    }

    def __init__(self, base_url: str = "https://fddm.autokeren.workers.dev", api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def _post(self, path: str, payload: dict[str, Any]) -> ToolResult:
        try:
            import httpx

            r = httpx.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self.headers(),
                timeout=30.0,
            )
            r.raise_for_status()
            return ToolResult(output=r.json())
        except Exception as e:
            return ToolResult(error=f"FDDM error: {e}", ok=False)

    def _get(self, path: str) -> ToolResult:
        try:
            import httpx

            r = httpx.get(f"{self.base_url}{path}", headers=self.headers(), timeout=30.0)
            r.raise_for_status()
            return ToolResult(output=r.json())
        except Exception as e:
            return ToolResult(error=f"FDDM error: {e}", ok=False)

    def run(self, **kwargs: Any) -> ToolResult:
        if not self.base_url:
            return ToolResult(error="FDDM belum dikonfigurasi. Aktifkan via /config fddm on atau isi fddm.url di config.yaml.", ok=False)

        action = kwargs.get("action", "")

        if action == "emit":
            return self._post(
                "/api/emit_text",
                {
                    "type": kwargs.get("type", "observation"),
                    "text": kwargs.get("text", ""),
                    "emitter_id": kwargs.get("emitter_id", "autokeren_agent"),
                    "base_score": 0.7,
                },
            )

        if action == "sniff":
            return self._post(
                "/api/sniff_text",
                {
                    "text": kwargs.get("text", ""),
                    "top_k": kwargs.get("top_k", 5),
                    "radius": kwargs.get("radius", 0.3),
                },
            )

        if action == "stats":
            return self._get("/api/stats")

        if action == "decay":
            return self._post("/api/decay", {})

        if action == "trust":
            return self._post(
                "/api/trust",
                {
                    "emitter_id": kwargs.get("emitter_id", "unknown"),
                    "success": kwargs.get("success", True),
                },
            )

        return ToolResult(error=f"Aksi FDDM tidak dikenal: {action}", ok=False)
# ak:d256cdb716990124
