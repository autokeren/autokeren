"""Reflector — evaluate hasil eksekusi, simpan lessons learned ke memory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autokeren.autoplan.decomposer import SubTask
from autokeren.autoplan.executor import ExecutionResult


@dataclass
class Lesson:
    """Satu pelajaran dari eksekusi sub-task."""
    task_title: str
    success: bool
    lesson: str
    pattern: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_title": self.task_title,
            "success": self.success,
            "lesson": self.lesson,
            "pattern": self.pattern,
        }


_REFLECT_PROMPT = """Evaluasi hasil eksekusi task berikut dan tarik pelajaran.

TASK: {task_title}
DESKRIPSI: {description}
SUCCESS CRITERIA: {criteria}
HASIL: {result}
STATUS: {success}

Buat pelajaran singkat (1-3 kalimat):
1. Apa yang berhasil/gagal?
2. Pattern apa yang bisa diulang/dihindari di masa depan?
3. Saran untuk task serupa berikutnya.

Format: teks biasa, langsung ke poin. Tanpa header.
"""


class Reflector:
    """Reflect pada setiap sub-task, kumpulkan lessons learned."""

    def __init__(self, router: Any = None, memory: Any = None) -> None:
        self.router = router
        self.memory = memory
        self.lessons: list[Lesson] = []

    def reflect(self, task: SubTask, result: ExecutionResult) -> Lesson | None:
        """Evaluate hasil, return Lesson, simpan ke memory."""
        if not self.router:
            lesson = self._heuristic_reflect(task, result)
        else:
            prompt = _REFLECT_PROMPT.format(
                task_title=task.title,
                description=task.description,
                criteria=task.success_criteria,
                result=result.output[:1000] if result.success else (result.error or result.output)[:1000],
                success="BERHASIL" if result.success else "GAGAL",
            )
            try:
                resp = self.router.complete(
                    [{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.2,
                )
                lesson_text = resp.content or ""
            except Exception:
                lesson_text = self._heuristic_reflect(task, result).lesson

            lesson = Lesson(
                task_title=task.title,
                success=result.success,
                lesson=lesson_text,
                pattern=self._extract_pattern(task, result),
            )

        self.lessons.append(lesson)
        self._save_to_memory(lesson)
        return lesson

    def _heuristic_reflect(self, task: SubTask, result: ExecutionResult) -> Lesson:
        """Fallback reflection tanpa LLM."""
        if result.success:
            lesson_text = f"Task '{task.title}' berhasil. Pendekatan yang dipakai efektif."
        else:
            lesson_text = (
                f"Task '{task.title}' gagal. Error: {result.error[:200]}. "
                f"Coba pendekatan berbeda atau pecah jadi sub-task lebih kecil."
            )
        return Lesson(
            task_title=task.title,
            success=result.success,
            lesson=lesson_text,
            pattern=self._extract_pattern(task, result),
        )

    @staticmethod
    def _extract_pattern(task: SubTask, result: ExecutionResult) -> str:
        """Extract pattern dari task title untuk kategorisasi."""
        title_lower = task.title.lower()
        patterns = {
            "test": "testing",
            "deploy": "deployment",
            "debug": "debugging",
            "fix": "bugfix",
            "create": "creation",
            "refactor": "refactoring",
            "config": "configuration",
            "build": "build",
            "setup": "setup",
            "install": "installation",
        }
        for keyword, label in patterns.items():
            if keyword in title_lower:
                return label
        return "general"

    def _save_to_memory(self, lesson: Lesson) -> None:
        """Simpan lesson ke persistent memory."""
        if not self.memory:
            return
        section = "autoplan_lessons" if lesson.success else "autoplan_failures"
        note = f"[{lesson.pattern}] {lesson.task_title}: {lesson.lesson}"
        try:
            self.memory.append(section, note)
        except Exception:
            pass

    def summary(self) -> str:
        """Ringkasan semua lessons."""
        if not self.lessons:
            return "Belum ada lessons."
        total = len(self.lessons)
        success = sum(1 for lesson in self.lessons if lesson.success)
        failed = total - success
        lines = [f"Total: {total} tasks | Sukses: {success} | Gagal: {failed}", ""]
        for lesson in self.lessons:
            icon = "✅" if lesson.success else "❌"
            lines.append(f"{icon} [{lesson.pattern}] {lesson.task_title}")
            lines.append(f"   → {lesson.lesson[:150]}")
        return "\n".join(lines)

    def get_patterns(self) -> dict[str, dict[str, int]]:
        """Return pattern stats: {pattern: {success: n, fail: n}}."""
        stats: dict[str, dict[str, int]] = {}
        for lesson in self.lessons:
            if lesson.pattern not in stats:
                stats[lesson.pattern] = {"success": 0, "fail": 0}
            if lesson.success:
                stats[lesson.pattern]["success"] += 1
            else:
                stats[lesson.pattern]["fail"] += 1
        return stats
# ak:41673cea7fb01306
