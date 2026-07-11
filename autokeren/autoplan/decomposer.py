"""SubTask and GoalDecomposer — pecah goal tingkat tinggi jadi sub-tasks."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SubTask:
    """Satu unit kerja dalam plan otonom."""
    id: str
    title: str
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    success_criteria: str = ""
    status: str = "pending"
    result: str = ""
    attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "depends_on": self.depends_on,
            "success_criteria": self.success_criteria,
            "status": self.status,
            "result": self.result,
            "attempts": self.attempts,
        }


_DECOMPOSE_PROMPT = """Kamu adalah planner AI. Pecah goal berikut menjadi sub-tasks yang executable.

GOAL: {goal}

CONTEXT (info project, memory, dll):
{context}

Aturan:
1. Buat 3-10 sub-tasks (tidak terlalu granular, tidak terlalu broad).
2. Setiap sub-task harus executable oleh agent coding (bisa pakai tool: read_file, write_file, patch_file, run_shell, search_code, dll).
3. Setiap sub-task punya success_criteria yang measurable.
4. Sebut dependency antar sub-task kalau ada (task B depends on task A).
5. Urutkan dari yang harus dikerjakan pertama.

Format output (JSON array, HANYA JSON tanpa penjelasan):
[
  {{
    "id": "t1",
    "title": " judul singkat",
    "description": "deskripsi detail apa yang harus dilakukan",
    "depends_on": [],
    "success_criteria": "kriteria sukses yang measurable"
  }},
  ...
]
"""


class GoalDecomposer:
    """Pecah goal tingkat tinggi jadi sub-tasks pakai LLM."""

    def __init__(self, router: Any = None, max_tasks: int = 10) -> None:
        self.router = router
        self.max_tasks = max_tasks

    def decompose(self, goal: str, context: str = "") -> list[SubTask]:
        """Return list of SubTask dari goal."""
        if not self.router:
            return self._fallback_decompose(goal)

        prompt = _DECOMPOSE_PROMPT.format(goal=goal, context=context or "(tidak ada context)")
        resp = self.router.complete(
            [{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.2,
        )
        raw = resp.content or "[]"
        return self._parse_tasks(raw)

    def _parse_tasks(self, raw: str) -> list[SubTask]:
        """Parse JSON array dari LLM response."""
        json_str = self._extract_json(raw)
        if not json_str:
            return []
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return []

        tasks: list[SubTask] = []
        for item in data[: self.max_tasks]:
            if not isinstance(item, dict):
                continue
            tid = item.get("id", f"t{len(tasks) + 1}")
            title = item.get("title", "").strip()
            if not title:
                continue
            tasks.append(SubTask(
                id=tid,
                title=title,
                description=item.get("description", ""),
                depends_on=item.get("depends_on", []),
                success_criteria=item.get("success_criteria", ""),
            ))
        return tasks

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON array dari text yang mungkin punya markdown fence."""
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return match.group(0)
        return ""

    def _fallback_decompose(self, goal: str) -> list[SubTask]:
        """Fallback tanpa LLM: single task."""
        return [SubTask(
            id="t1",
            title=goal,
            description="Eksekusi goal secara langsung tanpa decomposition.",
            success_criteria="Goal tercapai.",
        )]
# ak:6b7b72729e549fe4
