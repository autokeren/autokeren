"""Reddit source — .json public API."""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import httpx

from autokeren.research.models import Comment, ResearchContent, SearchResult


class RedditSource:
    """Reddit via .json endpoint (no auth needed)."""

    BASE = "https://www.reddit.com"

    def __init__(self, min_comment_score: int = 2, timeout: float = 15.0) -> None:
        self.min_comment_score = min_comment_score
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "reddit"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        url = f"{self.BASE}/search.json?q={quote(query)}&sort=relevance&t=year&limit={limit}"
        data = self._fetch_json(url)
        results: list[SearchResult] = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            results.append(SearchResult(
                id=d.get("id", ""),
                title=d.get("title", ""),
                url=f"{self.BASE}{d.get('permalink', '')}",
                source="reddit",
                score=d.get("score", 0),
                num_comments=d.get("num_comments", 0),
                created_utc=d.get("created_utc", 0.0),
                metadata={"subreddit": d.get("subreddit", "")},
            ))
        return results

    def get_content(self, url: str) -> ResearchContent | None:
        permalink = url.replace(self.BASE, "")
        if permalink.endswith("/"):
            permalink = permalink[:-1]
        json_url = f"{self.BASE}{permalink}.json"
        data = self._fetch_json(json_url)
        if not isinstance(data, list) or len(data) < 2:
            return None
        data_list: list[dict[str, Any]] = data if isinstance(data, list) else []
        if len(data_list) < 2:
            return None
        post_data = data_list[0].get("data", {}).get("children", [])
        if not post_data:
            return None
        post = post_data[0].get("data", {})
        comments = self._extract_comments(data_list[1].get("data", {}).get("children", []))
        return ResearchContent(
            title=post.get("title", ""),
            body=post.get("selftext", ""),
            author=post.get("author", ""),
            score=post.get("score", 0),
            url=url,
            source="reddit",
            comments=comments,
            total_comments=len(comments),
            metadata={"subreddit": post.get("subreddit", "")},
        )

    def _extract_comments(self, children: list[dict[str, Any]], depth: int = 0) -> list[Comment]:
        comments: list[Comment] = []
        for child in children:
            if child.get("kind") != "t1":
                continue
            d = child.get("data", {})
            body = d.get("body", "")
            if body in ("[deleted]", "[removed]") or len(body) < 20:
                continue
            score = d.get("score", 0)
            if score < self.min_comment_score and depth == 0:
                continue
            comment = Comment(
                author=d.get("author", "?"),
                body=body,
                score=score,
                depth=depth,
            )
            replies_data = d.get("replies", "")
            if isinstance(replies_data, dict) and "data" in replies_data:
                comment.replies = self._extract_comments(
                    replies_data["data"].get("children", []), depth + 1
                )
            comments.append(comment)
        return comments

    def _fetch_json(self, url: str) -> Any:
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
