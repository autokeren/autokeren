"""Research tool — agent-callable deep research tool."""
from __future__ import annotations

from typing import Any

from autokeren.research.orchestrator import ResearchOrchestrator
from autokeren.research.reddit import RedditSource
from autokeren.research.hackernews import HackerNewsSource
from autokeren.research.web import WebSource
from autokeren.tools.base import Tool, ToolResult


class ResearchTool(Tool):
    name = "research"
    description = (
        "Riset mendalam ke Reddit, Hacker News, dan web. "
        "Cari thread, baca komentar, rangkum temuan. "
        "Pakai untuk: riset pain points, design decisions, best practices."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Pertanyaan atau topik yang diriset"},
            "sources": {
                "type": "array",
                "items": {"type": "string", "enum": ["reddit", "hackernews", "web"]},
                "description": "Sumber yang dicari (default: semua)",
            },
            "depth": {"type": "integer", "description": "Jumlah thread yang di-fetch full (default: 3)"},
        },
        "required": ["query"],
    }
    requires_permission = False

    def __init__(
        self,
        router: Any = None,
        max_results: int = 10,
        max_depth: int = 3,
        summarize: bool = True,
        min_comment_score: int = 2,
    ) -> None:
        self.router = router
        self.max_results = max_results
        self.max_depth = max_depth
        self.summarize = summarize
        self.min_comment_score = min_comment_score

    def run(
        self,
        query: str = "",
        sources: list[str] | None = None,
        depth: int | None = None,
        **_: Any,
    ) -> ToolResult:
        if not query.strip():
            return ToolResult(error="query wajib diisi", ok=False)
        srcs: list[Any] = []
        enabled = sources or ["reddit", "hackernews", "web"]
        if "reddit" in enabled:
            srcs.append(RedditSource(min_comment_score=self.min_comment_score))
        if "hackernews" in enabled:
            srcs.append(HackerNewsSource(min_comment_score=self.min_comment_score))
        if "web" in enabled:
            srcs.append(WebSource())
        orchestrator = ResearchOrchestrator(
            sources=srcs,
            router=self.router,
            max_results=self.max_results,
            max_depth=self.max_depth,
            summarize=self.summarize,
            min_comment_score=self.min_comment_score,
        )
        report = orchestrator.research(query, depth=depth)
        output = orchestrator.format_report(report)
        return ToolResult(output=output)
