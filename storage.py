from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from models import TASK_STATUSES


@dataclass
class Task:
    id: str
    title: str
    tags: List[str]
    priority: Optional[str]
    status: str
    ts: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "Task":
        status_value = payload.get("status", "TODO")
        normalized_status = status_value.upper()
        if normalized_status not in TASK_STATUSES:
            normalized_status = "TODO"
        return cls(
            id=payload["id"],
            title=payload["title"],
            tags=list(payload.get("tags", [])),
            priority=payload.get("priority"),
            status=normalized_status,
            ts=payload["ts"],
        )


class TaskStorage:
    """Lightweight JSONL-backed store for backlog tasks."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = threading.Lock()

    def add_task(
        self, title: str, tags: Iterable[str], priority: Optional[str] = None
    ) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            tags=list(tags),
            priority=priority,
            status="TODO",
            ts=datetime.now(timezone.utc).isoformat(),
        )
        record = json.dumps(task.to_dict(), separators=(",", ":"))
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(record + "\n")
        return task

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return self._read_all()

    def update_task(
        self, task_id: str, *, status: Optional[str] = None, priority: Optional[str] = None
    ) -> Task:
        with self._lock:
            tasks = self._read_all()
            updated: Task | None = None
            for task in tasks:
                if task.id == task_id:
                    if status:
                        normalized = status.upper()
                        if normalized not in TASK_STATUSES:
                            normalized = "TODO"
                        task.status = normalized
                    if priority is not None:
                        task.priority = priority
                    updated = task
                    break
            if updated is None:
                raise LookupError(f"Task {task_id} not found")
            self._write_all(tasks)
            return updated

    def _read_all(self) -> List[Task]:
        tasks: List[Task] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tasks.append(Task.from_dict(payload))
        return tasks

    def _write_all(self, tasks: Iterable[Task]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            for task in tasks:
                handle.write(json.dumps(task.to_dict(), separators=(",", ":")) + "\n")


__all__ = ["Task", "TaskStorage"]
