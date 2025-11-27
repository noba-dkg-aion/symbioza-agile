import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import pytest
from fastapi.testclient import TestClient

from main import create_app
from storage import TaskStorage


@pytest.fixture()
def client(tmp_path: Path) -> Tuple[TestClient, TaskStorage, Path]:
    tasks_file = tmp_path / "tasks.jsonl"
    storage = TaskStorage(tasks_file)
    app = create_app(storage=storage)
    return TestClient(app), storage, tasks_file


def test_add_task_creates_jsonl_entry(client):
    http_client, storage, tasks_file = client
    response = http_client.post(
        "/v1/tasks/add",
        json={"title": "Draft API", "tags": ["backend"], "priority": "high"},
    )

    assert response.status_code == 201
    payload = response.json()["task"]
    assert payload["status"] == "TODO"
    assert payload["priority"] == "high"
    assert payload["tags"] == ["backend"]

    with tasks_file.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    assert len(lines) == 1

    tasks = storage.list_tasks()
    assert tasks[0].title == "Draft API"
    assert tasks[0].status == "TODO"


def test_update_task_allows_status_and_priority(client):
    http_client, storage, _ = client
    created = http_client.post(
        "/v1/tasks/add", json={"title": "Wire Kanban", "tags": []}
    ).json()["task"]

    response = http_client.post(
        "/v1/tasks/update",
        json={"id": created["id"], "status": "doing", "priority": "urgent"},
    )

    assert response.status_code == 200
    payload = response.json()["task"]
    assert payload["status"] == "DOING"
    assert payload["priority"] == "urgent"

    stored = storage.list_tasks()[0]
    assert stored.status == "DOING"
    assert stored.priority == "urgent"


def test_update_requires_at_least_one_field(client):
    http_client, _, _ = client
    http_client.post("/v1/tasks/add", json={"title": "Baseline"})
    # Missing both status and priority should trigger validation error
    response = http_client.post("/v1/tasks/update", json={"id": "invalid"})
    assert response.status_code == 422


def test_kanban_groups_all_statuses(client):
    http_client, _, tasks_file = client
    now = datetime.now(timezone.utc).isoformat()
    records = [
        {
            "id": "t1",
            "title": "Todo item",
            "tags": [],
            "priority": "low",
            "status": "TODO",
            "ts": now,
        },
        {
            "id": "t2",
            "title": "Doing item",
            "tags": [],
            "priority": "medium",
            "status": "DOING",
            "ts": now,
        },
        {
            "id": "t3",
            "title": "Done item",
            "tags": [],
            "priority": "high",
            "status": "DONE",
            "ts": now,
        },
    ]

    with tasks_file.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    response = http_client.get("/v1/tasks/kanban")
    assert response.status_code == 200
    board = response.json()["columns"]
    assert set(board.keys()) == {"TODO", "DOING", "DONE"}
    assert board["TODO"][0]["title"] == "Todo item"
    assert board["DONE"][0]["title"] == "Done item"
