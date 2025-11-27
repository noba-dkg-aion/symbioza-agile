from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from fastapi import Depends, FastAPI, HTTPException

from models import KanbanResponse, TaskCreate, TaskResponse, TaskUpdate, TASK_STATUSES
from storage import TaskStorage


def _backlog_path() -> Path:
    env_path = os.getenv("AGILE_TASKS_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).parent / "data" / "tasks.jsonl"


def create_app(storage: TaskStorage | None = None) -> FastAPI:
    store = storage or TaskStorage(_backlog_path())
    app = FastAPI(title="Symbioza Agile", version="0.1.0")

    def get_storage() -> TaskStorage:
        return store

    @app.post(
        "/v1/tasks/add",
        status_code=201,
        response_model=Dict[str, TaskResponse],
    )
    def add_task(
        payload: TaskCreate, storage: TaskStorage = Depends(get_storage)
    ) -> Dict[str, dict]:
        task = storage.add_task(payload.title, payload.tags, payload.priority)
        return {"task": task.to_dict()}

    @app.post(
        "/v1/tasks/update",
        response_model=Dict[str, TaskResponse],
    )
    def update_task(
        payload: TaskUpdate, storage: TaskStorage = Depends(get_storage)
    ) -> Dict[str, dict]:
        try:
            task = storage.update_task(
                payload.id,
                status=payload.status,
                priority=payload.priority,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return {"task": task.to_dict()}

    @app.get(
        "/v1/tasks/kanban",
        response_model=KanbanResponse,
    )
    def kanban(
        storage: TaskStorage = Depends(get_storage),
    ) -> Dict[str, Dict[str, List[dict]]]:
        board: Dict[str, List[dict]] = {status: [] for status in TASK_STATUSES}
        for task in storage.list_tasks():
            board.setdefault(task.status, []).append(task.to_dict())
        return {"columns": board}

    return app


app = create_app()
