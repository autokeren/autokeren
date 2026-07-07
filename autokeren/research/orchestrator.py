"""Research orchestrator — search, rank, fetch, summarize."""
from __future__ import annotations

import logging
from typing import Any

from autokeren.research.models import ResearchContent, ResearchReport, SearchResult

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """Research query: {query}

Berikut adalah {n} sumber yang ditemukan:

{context}

Buat laporan riset dengan format:
1. **Ringkasan Eksekutif** (2-3 kalimat)
2. **Temuan Utama** (bullet points, maksimal 10)
3. **Pain Points yang Teridentifikasi** (jika relevant)
4. **Saran/Rekomendasi** (berdasarkan temuan)
5. **Sumber** (URL + score)

Bahasa Indonesia.
"""


class ResearchOrchestrator:
    """Orchestrate deep research across multiple sources."""

    def __init__(
        self,
        sources: list[Any] | None = None,
        router: Any = None,
        max_results: int = 10,
        max_depth: int = 3,
        summarize: bool = True,
        min_comment_score: int = 2,
    ) -> None:
        self.sources = sources or []
        self.router = router
        self.max_results = max_results
        self.max_depth = max_depth
        self.summarize = summarize
        self.min_comment_score = min_comment_score

    def research(self, query: str, depth: int | None = None, summarize: bool | None = None) -> ResearchReport:
        d = depth if depth is not None else self.max_depth
        do_sum = summarize if summarize is not None else self.summarize
        all_results: list[SearchResult] = []
        for source in self.sources:
            try:
                results = source.search(query, limit=self.max_results)
                all_results.extend(results)
            except Exception as e:
                logger.warning("Search failed for %s: %s", getattr(source, "name", "?"), e)
        ranked = self._rank_results(all_results, query)
        top = ranked[: self.max_results]
        contents: list[ResearchContent] = []
        errors = 0
        for result in top[:d]:
            try:
                source = self._find_source(result.source)
                if source:
                    content = source.get_content(result.id if result.source == "hackernews" else result.url)
                    if content:
                        contents.append(content)
            except Exception as e:
                logger.warning("Fetch failed for %s: %s", result.url, e)
                errors += 1
        summary_text: str | None = None
        if do_sum and self.router and contents:
            summary_text = self._summarize(query, contents)
        return ResearchReport(
            query=query,
            results=top,
            contents=contents,
            summary=summary_text,
            metadata={"sources_used": [getattr(s, "name", "?") for s in self.sources], "errors": errors, "summarized": summary_text is not None},
        )

    def _rank_results(self, results: list[SearchResult], query: str) -> list[SearchResult]:
        q_lower = query.lower()
        scored: list[tuple[float, SearchResult]] = []
        for r in results:
            score = float(r.score)
            if q_lower in r.title.lower():
                score += 200
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]

    def _find_source(self, source_name: str) -> Any | None:
        for s in self.sources:
            if getattr(s, "name", "") == source_name:
                return s
        return None

    def _summarize(self, query: str, contents: list[ResearchContent]) -> str:
        context_parts: list[str] = []
        for c in contents:
            top_comments = "\n".join(
                f"  [{cm.score}] {cm.author}: {cm.body[:200]}"
                for cm in c.comments[:10]
                if cm.score >= self.min_comment_score
            )
            context_parts.append(
                f"### {c.title}\nScore: {c.score} | Comments: {c.total_comments}\n"
                f"Body: {c.body[:500]}\nTop comments:\n{top_comments}"
            )
        context = "\n\n".join(context_parts)
        prompt = _SUMMARY_PROMPT.format(query=query, n=len(contents), context=context)
        try:
            if self.router:
                resp = self.router.complete(
                    [{"role": "user", "content": prompt}],
                    max_tokens=2048,
                    temperature=0.3,
                )
                return resp.content or ""
        except Exception as e:
            logger.warning("Summarize failed: %s", e)
        return ""

    @staticmethod
    def format_report(report: ResearchReport) -> str:
        lines: list[str] = [f"# Research: {report.query}\n"]
        lines.append(f"Sources: {', '.join(report.metadata.get('sources_used', []))}")
        lines.append(f"Results: {len(report.results)} | Contents fetched: {len(report.contents)}\n")
        lines.append("## Search Results")
        for r in report.results:
            lines.append(f"- [{r.source}] {r.title} (score: {r.score}) — {r.url}")
        if report.contents:
            lines.append("\n## Content Summary")
            for c in report.contents:
                lines.append(f"### {c.title}")
                lines.append(f"  Source: {c.source} | Score: {c.score} | Comments: {c.total_comments}")
                if c.body:
                    lines.append(f"  Body: {c.body[:300]}...")
                if c.comments:
                    lines.append("  Top comments:")
                    for cm in c.comments[:5]:
                        lines.append(f"    [{cm.score}] {cm.author}: {cm.body[:150]}")
        if report.summary:
            lines.append("\n## LLM Summary")
            lines.append(report.summary)
        return "\n".join(lines)
