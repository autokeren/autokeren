"""Reviewer selector — pilih model berbeda vendor untuk review."""
from __future__ import annotations

_VENDOR_MAP: dict[str, str] = {
    "kimi-code": "glm-5.2",
    "kimi-2.6": "glm-flash",
    "glm-5.2": "kimi-code",
    "glm-flash": "kimi-2.6",
    "llama-4-scout": "kimi-code",
    "gemma-4": "glm-5.2",
    "nemotron": "kimi-2.6",
}


class ReviewerSelector:
    """Pilih reviewer model yang BERBEDA dari coder model."""

    def __init__(self, vendor_map: dict[str, str] | None = None) -> None:
        self.vendor_map = vendor_map or _VENDOR_MAP

    def select(self, coder_model: str) -> str:
        base = coder_model.split("/")[-1] if "/" in coder_model else coder_model
        return self.vendor_map.get(base, "glm-5.2")

    def is_different_vendor(self, coder: str, reviewer: str) -> bool:
        coder_base = coder.split("/")[-1] if "/" in coder else coder
        return coder_base != reviewer
