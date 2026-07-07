"""Spec planner — interview, plan generation, progress tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_QUESTION_PROMPT = """User ingin membangun: {request}

Buat {n} pertanyaan clarifying (Bahasa Indonesia) untuk memahami:
1. Scope & boundary
2. User personas
3. Data model
4. UI/UX
5. Integration
6. Performance
7. Security
8. Deployment
9. Testing
10. Future scaling

Format: numbered list, 1 pertanyaan per line.
"""

_PLAN_PROMPT = """Berdasarkan request dan jawaban interview, buat plan:

REQUEST: {request}

INTERVIEW Q&A:
{qa}

Buat 2 dokumen:
## plan.md (PRD)
- Overview
- User stories
- Feature list (P0, P1, P2)
- Out of scope

## technical-plan.md
- Architecture
- File structure
- Data model
- Implementation steps (ordered)
- Testing strategy
"""


@dataclass
class InterviewSession:
    request: str
    questions: list[str] = field(default_factory=list)
    answers: dict[str, str] = field(default_factory=dict)
    current: int = 0

    @property
    def is_complete(self) -> bool:
        return self.current >= len(self.questions)

    def answer(self, text: str) -> str | None:
        if self.current >= len(self.questions):
            return None
        q = self.questions[self.current]
        self.answers[q] = text
        self.current += 1
        if self.current < len(self.questions):
            return self.questions[self.current]
        return None

    def current_question(self) -> str | None:
        if self.current < len(self.questions):
            return self.questions[self.current]
        return None

    def format_qa(self) -> str:
        lines = []
        for q in self.questions:
            a = self.answers.get(q, "(tidak dijawab)")
            lines.append(f"Q: {q}\nA: {a}")
        return "\n\n".join(lines)


@dataclass
class SpecPlan:
    request: str
    plan_md: str = ""
    technical_md: str = ""
    steps: list[str] = field(default_factory=list)
    completed_steps: list[int] = field(default_factory=list)

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        return len(self.completed_steps) / len(self.steps) * 100

    def mark_done(self, step_idx: int) -> None:
        if step_idx not in self.completed_steps and 0 <= step_idx < len(self.steps):
            self.completed_steps.append(step_idx)

    def save(self, project_root: Path) -> None:
        (project_root / "plan.md").write_text(self.plan_md, encoding="utf-8")
        (project_root / "technical-plan.md").write_text(self.technical_md, encoding="utf-8")


class SpecPlanner:
    """Orchestrate spec-driven planning."""

    def __init__(self, router: Any = None, num_questions: int = 20) -> None:
        self.router = router
        self.num_questions = num_questions
        self._session: InterviewSession | None = None
        self._plan: SpecPlan | None = None

    @property
    def session(self) -> InterviewSession | None:
        return self._session

    @property
    def plan(self) -> SpecPlan | None:
        return self._plan

    def start_interview(self, request: str) -> InterviewSession:
        if self.router:
            prompt = _QUESTION_PROMPT.format(request=request, n=self.num_questions)
            resp = self.router.complete(
                [{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.3,
            )
            questions = self._parse_questions(resp.content or "")
        else:
            questions = self._default_questions(request)
        self._session = InterviewSession(request=request, questions=questions)
        return self._session

    def _parse_questions(self, text: str) -> list[str]:
        lines = []
        for line in text.strip().splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                cleaned = line.split(".", 1)[-1].strip() if "." in line else line
                if cleaned:
                    lines.append(cleaned)
        return lines[: self.num_questions] if lines else []

    def _default_questions(self, request: str) -> list[str]:
        all_qs = [
            "Apa tujuan utama dari project ini?",
            "Siapa target user-nya?",
            "Fitur apa saja yang wajib ada (P0)?",
            "Fitur apa yang nice-to-have (P1, P2)?",
            "Bagaimana struktur data yang dibutuhkan?",
            "Apakah perlu autentikasi? Jenisnya?",
            "Tech stack apa yang dipakai?",
            "Apakah perlu real-time features?",
            "Bagaimana strategi deployment?",
            "Apa yang harus di-test?",
        ]
        return all_qs[: self.num_questions]

    def generate_plan(self) -> SpecPlan | None:
        if not self._session or not self._session.is_complete:
            return None
        if self.router:
            prompt = _PLAN_PROMPT.format(
                request=self._session.request,
                qa=self._session.format_qa(),
            )
            resp = self.router.complete(
                [{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.3,
            )
            content = resp.content or ""
            plan_md, tech_md = self._split_plan(content)
            steps = self._extract_steps(tech_md)
        else:
            plan_md = "# Plan\n\n(Generate dengan LLM)"
            tech_md = "# Technical Plan\n\n(Generate dengan LLM)"
            steps = []
        self._plan = SpecPlan(
            request=self._session.request,
            plan_md=plan_md,
            technical_md=tech_md,
            steps=steps,
        )
        return self._plan

    def _split_plan(self, content: str) -> tuple[str, str]:
        if "## technical-plan.md" in content:
            parts = content.split("## technical-plan.md", 1)
            plan = parts[0].replace("## plan.md", "").strip()
            tech = parts[1].strip() if len(parts) > 1 else ""
            return plan, tech
        return content, ""

    def _extract_steps(self, tech_md: str) -> list[str]:
        import re
        steps = []
        for m in re.finditer(r"^\s*\d+\.\s+(.+)", tech_md, re.M):
            steps.append(m.group(1).strip())
        return steps
