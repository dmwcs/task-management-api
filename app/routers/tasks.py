from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.database import SessionDep
from app.models import (
    Tag,
    Task,
    TaskCreate,
    TaskListResponse,
    TaskRead,
    TaskTagLink,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_to_read(task: Task) -> TaskRead:
    """Convert a Task DB object to a TaskRead response model."""
    return TaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        due_date=task.due_date,
        completed=task.completed,
        created_at=task.created_at,
        updated_at=task.updated_at,
        tags=[tag.name for tag in task.tags],
    )


# POST /tasks — Create a new task with optional tags
@router.post("", status_code=201)
def create_task(task_data: TaskCreate, session: SessionDep) -> TaskRead:
    task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
    )

    for tag_name in set(task_data.tags):
        tag = session.exec(select(Tag).where(Tag.name == tag_name)).first()
        if not tag:
            tag = Tag(name=tag_name)
            session.add(tag)
        task.tags.append(tag)

    session.add(task)
    session.commit()
    session.refresh(task)
    return _task_to_read(task)


# GET /tasks — List tasks with filtering (completed, priority, tags) and pagination (limit, offset)
@router.get("")
def list_tasks(
    session: SessionDep,
    completed: bool | None = None,
    priority: int | None = None,
    tags: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> TaskListResponse:
    query = select(Task).where(Task.deleted_at == None)  # noqa: E711

    if completed is not None:
        query = query.where(Task.completed == completed)
    if priority is not None:
        query = query.where(Task.priority == priority)
    if tags:
        tag_names = [t.strip() for t in tags.split(",")]
        query = query.join(TaskTagLink).join(Tag).where(Tag.name.in_(tag_names))

    total = len(session.exec(query).all())
    tasks = session.exec(query.offset(offset).limit(limit)).all()

    return TaskListResponse(
        total=total,
        tasks=[_task_to_read(task) for task in tasks],
    )


# GET /tasks/{id} — Get a single task by ID, return 404 if not found or soft-deleted
@router.get("/{task_id}")
def get_task(task_id: int, session: SessionDep) -> TaskRead:
    task = session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_read(task)


# PATCH /tasks/{id} — Partial update, only modify fields provided in request body
@router.patch("/{task_id}")
def update_task(task_id: int, task_data: TaskUpdate, session: SessionDep) -> TaskRead:
    task = session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == "tags":
            task.tags.clear()
            for tag_name in value:
                tag = session.exec(select(Tag).where(Tag.name == tag_name)).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                task.tags.append(tag)
        else:
            setattr(task, key, value)

    task.updated_at = datetime.now()
    session.add(task)
    session.commit()
    session.refresh(task)
    return _task_to_read(task)


# DELETE /tasks/{id} — Soft delete by setting deleted_at timestamp
@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: SessionDep) -> None:
    task = session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Task not found")

    task.deleted_at = datetime.now()
    session.add(task)
    session.commit()
