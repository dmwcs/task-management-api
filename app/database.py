from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, create_engine

from app.config import settings

# Create the database engine (configures connection, does not connect yet)
engine = create_engine(settings.database_url)


# Dependency that provides a database session per request
# The session is automatically closed when the request is done
def get_session():
    with Session(engine) as session:
        yield session


# Type alias for dependency injection in route handlers
SessionDep = Annotated[Session, Depends(get_session)]
