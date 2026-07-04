"""Web fetch tool."""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx

from autokeren.tools.base import Tool, ToolResult

_BLOCKED_HOSTS = {"localhost", "0.0.0.0", "metadata.google.internal"}
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]


def _is_url_safe(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"scheme '{parsed.scheme}' not allowed"
    hostname = parsed.hostname or ""
    if hostname in _BLOCKED_HOSTS:
        return False, f"host '{hostname}' blocked"
    try:
        ip = ipaddress.ip_address(hostname)
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                return False, f"IP {ip} in private network"
    except ValueError:
        try:
            resolved = socket.getaddrinfo(hostname, None)
            for family, _, _, _, sockaddr in resolved:
                ip_str = sockaddr[0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    for net in _BLOCKED_NETWORKS:
                        if ip in net:
                            return False, f"host resolves to private IP {ip}"
                except ValueError:
                    pass
        except socket.gaierror:
            pass
    return True, ""


class FetchURLTool(Tool):
    name = "fetch_url"
    description = "Fetch a URL and return readable markdown-ish text. HTTP/HTTPS only, private networks blocked."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL to fetch (http/https only)."},
            "max_chars": {"type": "integer", "description": "Maximum characters to return.", "default": 5000},
        },
        "required": ["url"],
    }

    def run(self, url: str, max_chars: int = 5000, **_) -> ToolResult:
        safe, reason = _is_url_safe(url)
        if not safe:
            return ToolResult(error=f"blocked: {reason}", ok=False)
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
