"""Tests for Research tool — Reddit, HN, Web, Orchestrator."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from autokeren.research.models import ResearchContent, ResearchReport, SearchResult
from autokeren.research.reddit import RedditSource
from autokeren.research.hackernews import HackerNewsSource
from autokeren.research.orchestrator import ResearchOrchestrator
from autokeren.tools.research import ResearchTool


_REDDIT_SEARCH_JSON = {
    "data": {
        "children": [
            {
                "data": {
                    "id": "abc",
                    "title": "Best async framework?",
                    "permalink": "/r/python/comments/abc/best_async",
                    "score": 100,
                    "num_comments": 50,
                    "subreddit": "python",
                    "created_utc": 1700000000.0,
                }
            },
            {
                "data": {
                    "id": "def",
                    "title": "Python tips and tricks",
                    "permalink": "/r/python/comments/def/python_tips",
                    "score": 50,
                    "num_comments": 20,
                    "subreddit": "python",
                    "created_utc": 1700001000.0,
                }
            },
        ]
    }
}

_REDDIT_CONTENT_JSON = [
    {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Test Post",
                        "selftext": "Test body",
                        "author": "tester",
                        "score": 42,
                        "subreddit": "python",
                    }
                }
            ]
        }
    },
    {
        "data": {
            "children": [
                {
                    "kind": "t1",
                    "data": {
                        "author": "alice",
                        "body": "Great post! I really enjoyed reading this.",
                        "score": 15,
                        "replies": "",
                    },
                },
                {
                    "kind": "t1",
                    "data": {
                        "author": "bob",
                        "body": "Nice work, keep it up!",
                        "score": 8,
                        "replies": {
                            "data": {
                                "children": [
                                    {
                                        "kind": "t1",
                                        "data": {
                                            "author": "carol",
                                            "body": "I agree with bob, this is great content.",
                                            "score": 3,
                                            "replies": "",
                                        }
                                    }
                                ]
                            }
                        },
                    },
                },
            ]
        }
    },
]

_HN_SEARCH_JSON = {
    "hits": [
        {
            "objectID": "123",
            "title": "Best AI coding CLI",
            "url": "https://example.com/article",
            "points": 200,
            "num_comments": 50,
            "created_at_i": 1700000000,
        },
        {
            "objectID": "456",
            "title": "LLM vs coding agents",
            "url": "",
            "points": 150,
            "num_comments": 25,
            "created_at_i": 1700001000,
        },
    ]
}

_HN_CONTENT_JSON = {
    "title": "Best AI coding CLI",
    "url": "https://example.com/article",
    "author": "pg",
    "points": 200,
    "children": [
        {
            "text": "I use Claude daily for coding tasks.",
            "author": "alice",
            "points": 10,
            "children": [],
        },
        {
            "text": "Try autokeren, it's awesome for Cloudflare development.",
            "author": "bob",
            "points": 5,
            "children": [
                {
                    "text": "autokeren is great! I switched last week.",
                    "author": "carol",
                    "points": 2,
                    "children": [],
                }
            ],
        },
    ],
}


@patch("autokeren.research.reddit.httpx.get")
def test_reddit_search(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _REDDIT_SEARCH_JSON
    mock_get.return_value = mock_resp
    source = RedditSource()
    results = source.search("python async", limit=5)
    assert len(results) == 2
    assert results[0].title == "Best async framework?"
    assert results[0].source == "reddit"
    assert results[0].metadata["subreddit"] == "python"
    assert results[0].score == 100


@patch("autokeren.research.reddit.httpx.get")
def test_reddit_get_content(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _REDDIT_CONTENT_JSON
    mock_get.return_value = mock_resp
    source = RedditSource(min_comment_score=0)
    content = source.get_content("https://www.reddit.com/r/python/comments/abc/test_post")
    assert content is not None
    assert content.title == "Test Post"
    assert content.body == "Test body"
    assert content.author == "tester"
    assert content.score == 42
    assert len(content.comments) == 2
    assert content.comments[0].author == "alice"
    assert content.comments[1].replies[0].author == "carol"


@patch("autokeren.research.reddit.httpx.get")
def test_reddit_filter_deleted(mock_get):
    data = [
        {"data": {"children": [{"data": {"title": "T", "selftext": "", "author": "a", "score": 1, "subreddit": "x"}}]}},
        {"data": {"children": [
            {"kind": "t1", "data": {"author": "x", "body": "[deleted]", "score": 5, "replies": ""}},
            {"kind": "t1", "data": {"author": "y", "body": "short", "score": 5, "replies": ""}},
            {"kind": "t1", "data": {"author": "z", "body": "This is a valid comment with enough text.", "score": 5, "replies": ""}},
        ]}},
    ]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = data
    mock_get.return_value = mock_resp
    source = RedditSource(min_comment_score=0)
    content = source.get_content("https://www.reddit.com/r/x/comments/abc/t")
    assert content is not None
    assert len(content.comments) == 1
    assert content.comments[0].author == "z"


@patch("autokeren.research.hackernews.httpx.get")
def test_hn_search(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _HN_SEARCH_JSON
    mock_get.return_value = mock_resp
    source = HackerNewsSource()
    results = source.search("AI coding CLI", limit=5)
    assert len(results) == 2
    assert results[0].title == "Best AI coding CLI"
    assert results[0].source == "hackernews"
    assert results[0].score == 200
    assert results[1].url == "https://news.ycombinator.com/item?id=456"


@patch("autokeren.research.hackernews.httpx.get")
def test_hn_get_content(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _HN_CONTENT_JSON
    mock_get.return_value = mock_resp
    source = HackerNewsSource(min_comment_score=0)
    content = source.get_content("123")
    assert content is not None
    assert content.title == "Best AI coding CLI"
    assert content.author == "pg"
    assert len(content.comments) == 2
    assert content.comments[1].replies[0].author == "carol"


def test_orchestrator_rank_results():
    results = [
        SearchResult(id="1", title="Python async guide", source="reddit", score=100),
        SearchResult(id="2", title="JavaScript promises", source="reddit", score=200),
        SearchResult(id="3", title="Python tips", source="hackernews", score=50),
    ]
    orch = ResearchOrchestrator(sources=[])
    ranked = orch._rank_results(results, "python async")
    assert ranked[0].title == "Python async guide"
    assert ranked[1].title == "JavaScript promises"


def test_orchestrator_no_sources():
    orch = ResearchOrchestrator(sources=[])
    report = orch.research("test query", depth=0)
    assert report.query == "test query"
    assert len(report.results) == 0
    assert len(report.contents) == 0


def test_orchestrator_format_report():
    report = ResearchReport(
        query="test",
        results=[SearchResult(id="1", title="Result 1", url="https://example.com", source="reddit", score=10)],
        contents=[ResearchContent(title="Content 1", body="Body text", source="reddit", score=5, total_comments=2)],
        summary="Summary text",
    )
    formatted = ResearchOrchestrator.format_report(report)
    assert "test" in formatted
    assert "Result 1" in formatted
    assert "Content 1" in formatted
    assert "Summary text" in formatted


def test_research_tool_no_query():
    tool = ResearchTool()
    result = tool.run()
    assert not result.ok
    assert "query" in (result.error or "").lower()


def test_research_tool_empty_sources():
    tool = ResearchTool()
    result = tool.run(query="test", sources=[], depth=0)
    assert result.ok


class _MockSource:
    """Mock source for orchestrator tests."""

    def __init__(self, name: str, results: list[SearchResult], content: ResearchContent | None = None):
        self._name = name
        self._results = results
        self._content = content

    @property
    def name(self) -> str:
        return self._name

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        return self._results

    def get_content(self, item_id: str) -> ResearchContent | None:
        return self._content


def test_orchestrator_with_mock_sources():
    reddit_results = [SearchResult(id="r1", title="Reddit Result", source="reddit", score=100, url="https://reddit.com/r1")]
    hn_results = [SearchResult(id="h1", title="HN Result", source="hackernews", score=50, url="https://hn.com/h1")]
    content = ResearchContent(title="Reddit Result", body="Body", source="reddit", score=100, total_comments=5)
    sources = [
        _MockSource("reddit", reddit_results, content),
        _MockSource("hackernews", hn_results),
    ]
    orch = ResearchOrchestrator(sources=sources, max_results=10, max_depth=1, summarize=False)
    report = orch.research("test", depth=1)
    assert len(report.results) == 2
    assert len(report.contents) == 1
    assert report.contents[0].title == "Reddit Result"
