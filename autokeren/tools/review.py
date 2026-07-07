"""Cross-Model Review tool — review code dengan model berbeda."""
from __future__ import annotations

import subprocess
from typing import Any

from autokeren.review.selector import ReviewerSelector
from autokeren.review.parser import format_review_for_agent, parse_review_output
from autokeren.tools.base import Tool, ToolResult

_REVIEW_PROMPT = """Review code diff berikut. Cek: bugs, security, architecture, edge cases.

Diff:
{diff}

Format output:
SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
ISSUE: <description>
FILE: <path>:<line>
FIX: <suggested fix>

Jika tidak ada issue, katakan: "NO ISSUES FOUND"
"""


class ReviewTool(Tool):
    name = "review"
    description = (
        "Review code dengan model berbeda untuk catch blind spots. "
        "Mengirim diff ke reviewer model (beda vendor) untuk check bugs, security, architecture."
    )
    parameters = {
        "type": "object",
        "properties": {
            "diff": {
                "type": "string",
                "description": "Git diff atau code changes untuk di-review",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File yang berubah (opsional, untuk context)",
            },
        },
        "required": ["diff"],
    }

    def __init__(self, project_root: str, coder_model: str = "", router=None) -> None:
        self.project_root = project_root
        self.coder_model = coder_model
        self.router = router
        self.selector = ReviewerSelector()

    def run(self, diff: str, files: list[str] | None = None, **_: Any) -> ToolResult:
        if not diff.strip():
            return ToolResult(output="Tidak ada diff untuk di-review.")
        reviewer_model = self.selector.select(self.coder_model)
        prompt = _REVIEW_PROMPT.format(diff=diff[:8000])
        try:
            if self.router:
                from autokeren.models.base import ModelResponse
                resp: ModelResponse = self.router.complete(
                    [{"role": "user", "content": prompt}],
                    max_tokens=2048,
                    temperature=0.0,
                )
                raw_output = resp.content or ""
            else:
                return ToolResult(error="Router tidak tersedia untuk review", ok=False)
        except Exception as e:
            return ToolResult(error=f"Review gagal: {e}", ok=False)
        result = parse_review_output(raw_output, reviewer_model)
        formatted = format_review_for_agent(result)
        return ToolResult(output=formatted)


def collect_git_diff(project_root: str, staged: bool = False) -> str:
    """Collect git diff dari project."""
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=project_root, timeout=10
        )
        return result.stdout
    except Exception:
        return ""
