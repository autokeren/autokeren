"""Data models for research module."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Comment:
    author: str = ""
    body: str = ""
    score: int = 0
    depth: int = 0
    replies: list[Comment] = field(default_factory=list)


@dataclass
class SearchResult:
    id: str = ""
    title: str = ""
    url: str = ""
    source: str = ""
    score: int = 0
    num_comments: int = 0
    created_utc: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchContent:
    title: str = ""
    body: str = ""
    author: str = ""
    score: int = 0
    url: str = ""
    source: str = ""
    comments: list[Comment] = field(default_factory=list)
    total_comments: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchReport:
    query: str = ""
    results: list[SearchResult] = field(default_factory=list)
    contents: list[ResearchContent] = field(default_factory=list)
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
