from datetime import date, datetime

from pydantic import BaseModel, field_validator
from sqlmodel import Field, Relationship, SQLModel


# ---- Link Table (many-to-many) ----
class TaskTagLink(SQLModel, table=True):
    task_id: int = Field(foreign_key="task.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


# ---- Database Tables ----
class Tag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)

    tasks: list["Task"] = Relationship(back_populates="tags", link_model=TaskTagLink)


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: str | None = None
    priority: int = Field(ge=1, le=5, index=True)
    due_date: date
    completed: bool = Field(default=False, index=True)
    deleted_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    tags: list[Tag] = Relationship(back_populates="tasks", link_model=TaskTagLink)


# ---- Request Models ----
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: int = Field(ge=1, le=5)
    due_date: date
    tags: list[str] = []

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Due date cannot be in the past")
        return v


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    due_date: date | None = None
    completed: bool | None = None
    tags: list[str] | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("Due date cannot be in the past")
        return v


# ---- Response Models ----
class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None
    priority: int
    due_date: date
    completed: bool
    created_at: datetime
    updated_at: datetime
    tags: list[str]


class TaskListResponse(BaseModel):
    total: int
    tasks: list[TaskRead]
