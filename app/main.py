from fastapi import FastAPI
from sqlmodel import SQLModel

from app.database import engine

app = FastAPI(title="Task Management API")

SQLModel.metadata.create_all(engine)
print("Database connected and tables created")
