"""Web source — DuckDuckGo HTML search + fetch."""
from __future__ import annotations

import re
from urllib.parse import quote

import httpx

from autokeren.research.models import ResearchContent, SearchResult


class WebSource:
    """General web via DuckDuckGo HTML (no API key needed)."""

    SEARCH_URL = "https://html.duckduckgo.com/html/"
    HEADERS = {"User-Agent": "autokeren/research bot"}

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "web"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        resp = self._fetch_html(f"{self.SEARCH_URL}?q={quote(query)}")
        results: list[SearchResult] = []
        for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp, re.S):
            url = m.group(1)
            if url.startswith("//"):
                url = "https:" + url
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if title and url:
                results.append(SearchResult(
                    id=url,
                    title=title,
                    url=url,
                    source="web",
                    score=0,
                    metadata={},
                ))
            if len(results) >= limit:
                break
        return results

    def get_content(self, url: str) -> ResearchContent | None:
        html = self._fetch_html(url)
        if not html:
            return None
        title = self._extract_title(html)
        text = self._html_to_text(html)
        return ResearchContent(
            title=title,
            body=text[:10000],
            url=url,
            source="web",
            metadata={},
        )

    def _fetch_html(self, url: str) -> str:
        for attempt in range(3):
            try:
                resp = httpx.get(url, headers=self.HEADERS, timeout=self.timeout, follow_redirects=True)
                if resp.status_code == 200:
                    return resp.text
            except Exception:
                pass
        return ""

    @staticmethod
    def _extract_title(html: str) -> str:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _html_to_text(html: str) -> str:
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S | re.I)
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"\s+", " ", html)
        return html.strip()
