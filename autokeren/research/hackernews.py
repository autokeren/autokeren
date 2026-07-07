"""Hacker News source — Algolia API."""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import httpx

from autokeren.research.models import Comment, ResearchContent, SearchResult


class HackerNewsSource:
    """HN via Algolia API (no auth needed)."""

    BASE = "https://hn.algolia.com/api/v1"

    def __init__(self, min_comment_score: int = 2, timeout: float = 15.0) -> None:
        self.min_comment_score = min_comment_score
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "hackernews"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        url = f"{self.BASE}/search?query={quote(query)}&tags=story&hitsPerPage={limit}"
        data = self._fetch_json(url)
        results: list[SearchResult] = []
        for hit in data.get("hits", []):
            oid = hit.get("objectID", "")
            results.append(SearchResult(
                id=oid,
                title=hit.get("title", ""),
                url=hit.get("url", "") or f"https://news.ycombinator.com/item?id={oid}",
                source="hackernews",
                score=hit.get("points", 0),
                num_comments=hit.get("num_comments", 0),
                created_utc=float(hit.get("created_at_i", 0)),
                metadata={},
            ))
        return results

    def get_content(self, item_id: str) -> ResearchContent | None:
        url = f"{self.BASE}/items/{item_id}"
        data = self._fetch_json(url)
        if not data:
            return None
        comments = self._extract_comments(data.get("children", []))
        return ResearchContent(
            title=data.get("title", ""),
            body=data.get("url", ""),
            author=data.get("author", ""),
            score=data.get("points", 0),
            url=f"https://news.ycombinator.com/item?id={item_id}",
            source="hackernews",
            comments=comments,
            total_comments=len(comments),
            metadata={},
        )

    def _extract_comments(self, children: list[dict[str, Any]], depth: int = 0) -> list[Comment]:
        comments: list[Comment] = []
        for child in children:
            d = child if isinstance(child, dict) else {}
            body = d.get("text", "")
            if not body or len(body) < 20:
                continue
            score = d.get("points", 0) or 0
            if depth == 0 and score < self.min_comment_score:
                continue
            comment = Comment(
                author=d.get("author", "?"),
                body=body,
                score=score,
                depth=depth,
            )
            comment.replies = self._extract_comments(d.get("children", []), depth + 1)
            comments.append(comment)
        return comments

    def _fetch_json(self, url: str) -> dict[str, Any]:
        headers = {"User-Agent": "autokeren/research bot"}
        for attempt in range(3):
            try:
                resp = httpx.get(url, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 429:
                    time.sleep(2)
                    continue
            except Exception:
                time.sleep(1)
        return {}
