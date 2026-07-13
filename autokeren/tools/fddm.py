"""FDDM Tool — Feromon Digital Distributed Memory integration."""
from __future__ import annotations

from typing import Any

from autokeren.tools.base import Tool, ToolResult

FDDM_DEFAULT_URL = "https://autokeren-b6481c9f.pyscalp.workers.dev"


class FDDMTool(Tool):
    name = "fddm"
    description = (
        "Operasi FDDM (Feromon Digital Distributed Memory) — memori kolektif antar agent. "
        "Aksi: emit (simpan memori), sniff (cari memori relevan), stats (lihat statistik), "
        "decay (jalankan pemudaran), trust (lapor kepercayaan emitter), curiosity (cari jejak lemah)."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["emit", "sniff", "stats", "decay", "trust", "curiosity"],
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
                "description": "Jumlah hasil maksimal (untuk sniff/curiosity). Default 5.",
            },
            "radius": {
                "type": "number",
                "description": "Minimum similarity (0-1) untuk sniff. Default 0.5.",
            },
            "success": {
                "type": "boolean",
                "description": "Apakah emitter berhasil membantu (untuk trust).",
            },
        },
        "required": ["action"],
    }

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or FDDM_DEFAULT_URL).rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> ToolResult:
        try:
            import httpx

            r = httpx.post(f"{self.base_url}{path}", json=payload, timeout=30.0)
            r.raise_for_status()
            return ToolResult(output=r.json())
        except Exception as e:
            return ToolResult(error=f"FDDM error: {e}", ok=False)

    def _get(self, path: str) -> ToolResult:
        try:
            import httpx

            r = httpx.get(f"{self.base_url}{path}", timeout=30.0)
            r.raise_for_status()
            return ToolResult(output=r.json())
        except Exception as e:
            return ToolResult(error=f"FDDM error: {e}", ok=False)

    def run(self, **kwargs: Any) -> ToolResult:
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

        if action == "curiosity":
            return self._post(
                "/api/curiosity",
                {
                    "focus_vector": kwargs.get("text", ""),
                    "radius": kwargs.get("radius", 0.3),
                },
            )

        return ToolResult(error=f"Aksi FDDM tidak dikenal: {action}", ok=False)
# ak:3bb28d60e5a5da3f
