from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel

from app.database import engine
from app.models import Task, Tag, TaskTagLink  # noqa: F401
from app.routers import tasks

app = FastAPI(title="Task Management API")
app.include_router(tasks.router)


# Custom error handler to match the required error format
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = {}
    for error in exc.errors():
        field = error["loc"][-1]
        details[field] = error["msg"]
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Failed", "details": details},
    )


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    print("Database connected and tables created")
