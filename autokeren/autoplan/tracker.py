"""PlanTracker — track status semua sub-tasks dalam plan otonom."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from autokeren.autoplan.decomposer import SubTask


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanTracker:
    """Track progress semua sub-tasks."""
    tasks: list[SubTask] = field(default_factory=list)
    _status: dict[str, TaskStatus] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for t in self.tasks:
            if t.id not in self._status:
                self._status[t.id] = TaskStatus.PENDING

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        self._status[task_id] = status
        for t in self.tasks:
            if t.id == task_id:
                t.status = status.value
                break

    def get_status(self, task_id: str) -> TaskStatus:
        return self._status.get(task_id, TaskStatus.PENDING)

    def get_ready_tasks(self) -> list[SubTask]:
        """Return tasks yang ready untuk dikerjakan (deps semua done)."""
        ready: list[SubTask] = []
        for t in self.tasks:
            if self._status.get(t.id) not in (TaskStatus.PENDING, TaskStatus.READY):
                continue
            if self._deps_satisfied(t):
                ready.append(t)
        return ready

    def _deps_satisfied(self, task: SubTask) -> bool:
        if not task.depends_on:
            return True
        for dep_id in task.depends_on:
            if self._status.get(dep_id, TaskStatus.PENDING) != TaskStatus.DONE:
                return False
        return True

    def all_done(self) -> bool:
        return all(
            self._status.get(t.id) in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.SKIPPED)
            for t in self.tasks
        )

    def summary(self) -> str:
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if self._status.get(t.id) == TaskStatus.DONE)
        failed = sum(1 for t in self.tasks if self._status.get(t.id) == TaskStatus.FAILED)
        pending = sum(1 for t in self.tasks if self._status.get(t.id) in (TaskStatus.PENDING, TaskStatus.READY))
        in_progress = sum(1 for t in self.tasks if self._status.get(t.id) == TaskStatus.IN_PROGRESS)
        return f"{total} tasks — done:{done} in_progress:{in_progress} failed:{failed} pending:{pending}"

    def progress_pct(self) -> float:
        if not self.tasks:
            return 0.0
        done = sum(1 for t in self.tasks if self._status.get(t.id) == TaskStatus.DONE)
        return round(done / len(self.tasks) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "progress": self.progress_pct(),
            "tasks": [
                {**t.to_dict(), "status": self._status.get(t.id, TaskStatus.PENDING).value}
                for t in self.tasks
            ],
        }
# ak:b6052da2b0c6533a
