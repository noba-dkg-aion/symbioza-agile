from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

TASK_STATUSES: Tuple[str, ...] = ("TODO", "DOING", "DONE")


class TaskCreate(BaseModel):
    title: str = Field(..., description="Short summary for the backlog entry")
    tags: List[str] = Field(default_factory=list)
    priority: Optional[str] = Field(
        default=None, description="Optional priority label such as low/med/high"
    )

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title cannot be blank")
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def _trim_tags(cls, tags: Iterable[str]) -> List[str]:
        return [tag.strip() for tag in tags or []]


class TaskUpdate(BaseModel):
    id: str = Field(..., description="Task identifier returned from the add endpoint")
    status: Optional[str] = Field(default=None, description="Updated status (TODO/DOING/DONE)")
    priority: Optional[str] = Field(default=None, description="Updated priority label")

    @field_validator("status")
    @classmethod
    def _status_normalized(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().upper()
        if normalized not in TASK_STATUSES:
            raise ValueError(f"status must be one of {', '.join(TASK_STATUSES)}")
        return normalized

    @model_validator(mode="after")
    def _validate_changes(self) -> "TaskUpdate":
        if self.status is None and self.priority is None:
            raise ValueError("At least one field (status or priority) must be provided")
        return self


class TaskResponse(BaseModel):
    id: str
    title: str
    tags: List[str]
    priority: Optional[str]
    status: str
    ts: str


class KanbanResponse(BaseModel):
    columns: Dict[str, List[TaskResponse]]
