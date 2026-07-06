"""autokeren.multiagent — Manajemen project multi-agent."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class WorkerStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentWorker:
    """Satu agent yang mengerjakan satu task secara independen."""

    name: str
    task: str
    status: WorkerStatus = WorkerStatus.PENDING
    output: str = ""
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    # Runtime — diisi setelah run()
    _thread: threading.Thread | None = field(default=None, repr=False, compare=False)
    _agent: Any | None = field(default=None, repr=False, compare=False)

    def elapsed(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.finished_at if self.finished_at else time.time()
        return end - self.started_at

    def status_icon(self) -> str:
        icons = {
            WorkerStatus.PENDING: "⏳",
            WorkerStatus.RUNNING: "🟡",
            WorkerStatus.DONE: "✅",
            WorkerStatus.ERROR: "❌",
        }
        return icons.get(self.status, "?")


@dataclass
class AgentProject:
    """Container untuk sekelompok AgentWorker yang bekerja bersama."""

    name: str
    workers: list[AgentWorker] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_worker(self, name: str, task: str) -> AgentWorker:
        """Tambah worker baru ke project."""
        for w in self.workers:
            if w.name == name:
                raise ValueError(f"Worker '{name}' sudah ada di project '{self.name}'.")
        worker = AgentWorker(name=name, task=task)
        self.workers.append(worker)
        return worker

    def get_worker(self, name: str) -> AgentWorker | None:
        return next((w for w in self.workers if w.name == name), None)

    def summary(self) -> str:
        total = len(self.workers)
        done = sum(1 for w in self.workers if w.status == WorkerStatus.DONE)
        running = sum(1 for w in self.workers if w.status == WorkerStatus.RUNNING)
        error = sum(1 for w in self.workers if w.status == WorkerStatus.ERROR)
        return f"{total} workers — ✅{done} 🟡{running} ❌{error}"

    def all_done(self) -> bool:
        return all(w.status in (WorkerStatus.DONE, WorkerStatus.ERROR) for w in self.workers)


class ProjectManager:
    """Mengelola semua AgentProject dalam satu sesi."""

    def __init__(self) -> None:
        self.projects: dict[str, AgentProject] = {}
        self.active_project: str | None = None

    def new_project(self, name: str) -> AgentProject:
        if name in self.projects:
            raise ValueError(f"Project '{name}' sudah ada.")
        project = AgentProject(name=name)
        self.projects[name] = project
        self.active_project = name
        return project

    def get_active(self) -> AgentProject | None:
        if not self.active_project:
            return None
        return self.projects.get(self.active_project)

    def switch(self, name: str) -> AgentProject:
        if name not in self.projects:
            raise ValueError(f"Project '{name}' tidak ditemukan.")
        self.active_project = name
        return self.projects[name]

    def run_project(
        self,
        project: AgentProject,
        agent_factory: Callable[[str], Any],
        on_worker_done: Callable[[AgentWorker], None] | None = None,
    ) -> None:
        """Jalankan semua PENDING worker di project secara paralel di thread terpisah."""

        def _run_worker(worker: AgentWorker, agent: Any) -> None:
            worker._agent = agent
            worker.status = WorkerStatus.RUNNING
            worker.started_at = time.time()
            try:
                result = agent.run(worker.task)
                worker.output = result or ""
                worker.status = WorkerStatus.DONE
            except Exception as exc:
                worker.error = str(exc)
                worker.status = WorkerStatus.ERROR
            finally:
                worker.finished_at = time.time()
                if on_worker_done:
                    on_worker_done(worker)

        for worker in project.workers:
            if worker.status != WorkerStatus.PENDING:
                continue
            agent = agent_factory(worker.name)
            t = threading.Thread(target=_run_worker, args=(worker, agent), daemon=True)
            worker._thread = t
            t.start()
