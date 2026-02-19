from fastapi import FastAPI
from sqlmodel import SQLModel

from app.database import engine
from app.models import Task, Tag, TaskTagLink  # noqa: F401
from app.routers import tasks

app = FastAPI(title="Task Management API")
app.include_router(tasks.router)

SQLModel.metadata.create_all(engine)
print("Database connected and tables created")
