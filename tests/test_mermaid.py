"""Tests for mermaid diagram parser."""
from __future__ import annotations

import pytest

from autokeren.mermaid import extract_mermaid_blocks, extract_and_render, render_mermaid_text
from rich.console import Console


class TestExtractMermaid:
    def test_extract_single_block(self) -> None:
        text = "blah\n```mermaid\nsequenceDiagram\nA->>B: hello\n```\nmore"
        blocks = extract_mermaid_blocks(text)
        assert len(blocks) == 1
        assert "sequenceDiagram" in blocks[0]

    def test_extract_multiple_blocks(self) -> None:
        text = "```mermaid\ngraph TD\nA-->B\n```\nmid\n```mermaid\nsequenceDiagram\nC->>D: hi\n```"
        blocks = extract_mermaid_blocks(text)
        assert len(blocks) == 2

    def test_no_blocks(self) -> None:
        assert extract_mermaid_blocks("just text") == []

    def test_empty_block(self) -> None:
        assert extract_mermaid_blocks("```mermaid\n```") == []


class TestRenderSequence:
    def test_render_basic_sequence(self) -> None:
        code = """sequenceDiagram
    participant A as Alice
    participant B as Bob
    A->>B: Hello
    B-->>A: Hi"""
        console = Console(record=True, width=100)
        render_mermaid_text(code, console)
        output = console.export_text()
        assert "Alice" in output
        assert "Bob" in output
        assert "Hello" in output

    def test_render_loop(self) -> None:
        code = """sequenceDiagram
    A->>B: start
    loop 3 times
        B->>B: process
    end
    B-->>A: done"""
        console = Console(record=True, width=100)
        render_mermaid_text(code, console)
        output = console.export_text()
        assert "process" in output

    def test_render_alt(self) -> None:
        code = """sequenceDiagram
    A->>B: check
    alt success
        B-->>A: ok
    else fail
        B-->>A: error
    end"""
        console = Console(record=True, width=100)
        render_mermaid_text(code, console)
        output = console.export_text()
        assert "ok" in output
        assert "error" in output


class TestRenderFlowchart:
    def test_render_basic_flowchart(self) -> None:
        code = """graph TD
    A[Start] --> B[End]"""
        console = Console(record=True, width=100)
        render_mermaid_text(code, console)
        output = console.export_text()
        assert "Start" in output or "A" in output


class TestExtractAndRender:
    def test_full_pipeline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Force text fallback (no network in tests)
        import autokeren.mermaid as mm
        monkeypatch.setattr(mm, "_can_render_image", lambda: False)

        text = """Here's a diagram:

```mermaid
sequenceDiagram
    User->>Web: Click
    Web-->>User: Response
```

Done."""
        console = Console(record=True, width=100)
        extract_and_render(text, console)
        output = console.export_text()
        assert "User" in output
        assert "Web" in output

    def test_no_mermaid_no_output(self) -> None:
        console = Console(record=True, width=100)
        extract_and_render("just regular text", console)
        output = console.export_text()
        assert output.strip() == ""
