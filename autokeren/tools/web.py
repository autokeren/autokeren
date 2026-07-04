"""Web fetch tool."""
from __future__ import annotations

import re

import httpx

from autokeren.tools.base import Tool, ToolResult


class FetchURLTool(Tool):
    name = "fetch_url"
    description = "Fetch a URL and return readable markdown-ish text."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL to fetch."},
            "max_chars": {"type": "integer", "description": "Maximum characters to return.", "default": 5000},
        },
        "required": ["url"],
    }

    def run(self, url: str, max_chars: int = 5000, **_) -> ToolResult:
        try:
            r = httpx.get(url, timeout=30, follow_redirects=True, headers={"User-Agent": "autokeren/0.1"})
            r.raise_for_status()
            text = self._to_text(r.text)
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n... truncated from {len(text)} chars"
            return ToolResult(output=text)
        except Exception as e:
            return ToolResult(error=f"{type(e).__name__}: {e}", ok=False)

    def _to_text(self, html: str) -> str:
        # Strip script/style tags and excessive whitespace
        text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        return text.strip()
