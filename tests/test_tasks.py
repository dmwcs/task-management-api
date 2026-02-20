import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app

# Use SQLite in-memory database for testing
# StaticPool ensures all connections share the same in-memory database
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="client")
def client_fixture():
    SQLModel.metadata.create_all(test_engine)

    def get_test_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(test_engine)


# Helper to create a valid task payload
def task_payload(**overrides):
    data = {
        "title": "Test Task",
        "priority": 3,
        "due_date": "2026-12-31",
        "tags": ["work"],
    }
    data.update(overrides)
    return data


# ---- POST /tasks ----

def test_create_task_success(client):
    response = client.post("/tasks", json=task_payload())
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["priority"] == 3
    assert data["tags"] == ["work"]
    assert data["id"] is not None


def test_create_task_with_multiple_tags(client):
    response = client.post("/tasks", json=task_payload(tags=["work", "urgent"]))
    assert response.status_code == 201
    assert sorted(response.json()["tags"]) == ["urgent", "work"]


def test_create_task_missing_title(client):
    payload = task_payload()
    del payload["title"]
    response = client.post("/tasks", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_create_task_priority_out_of_range(client):
    response = client.post("/tasks", json=task_payload(priority=10))
    assert response.status_code == 422
    assert "detail" in response.json()


def test_create_task_due_date_in_past(client):
    response = client.post("/tasks", json=task_payload(due_date="2020-01-01"))
    assert response.status_code == 422
    assert "detail" in response.json()


def test_create_task_title_too_long(client):
    response = client.post("/tasks", json=task_payload(title="x" * 201))
    assert response.status_code == 422
    assert "detail" in response.json()


# ---- GET /tasks ----

def test_list_tasks_empty(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["tasks"] == []


def test_list_tasks_pagination(client):
    for i in range(5):
        client.post("/tasks", json=task_payload(title=f"Task {i}"))
    response = client.get("/tasks?limit=2&offset=0")
    data = response.json()
    assert data["total"] == 5
    assert len(data["tasks"]) == 2


def test_list_tasks_filter_by_priority(client):
    client.post("/tasks", json=task_payload(title="High", priority=5))
    client.post("/tasks", json=task_payload(title="Low", priority=1))
    response = client.get("/tasks?priority=5")
    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["title"] == "High"


def test_list_tasks_filter_by_tags(client):
    client.post("/tasks", json=task_payload(title="Work", tags=["work"]))
    client.post("/tasks", json=task_payload(title="Personal", tags=["personal"]))
    response = client.get("/tasks?tags=work")
    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["title"] == "Work"


# ---- GET /tasks/{id} ----

def test_get_task_success(client):
    create_response = client.post("/tasks", json=task_payload())
    task_id = create_response.json()["id"]
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Task"


def test_get_task_not_found(client):
    response = client.get("/tasks/999")
    assert response.status_code == 404


# ---- PATCH /tasks/{id} ----

def test_update_task_partial(client):
    create_response = client.post("/tasks", json=task_payload())
    task_id = create_response.json()["id"]
    response = client.patch(f"/tasks/{task_id}", json={"title": "Updated"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    assert response.json()["priority"] == 3  # unchanged


def test_update_task_tags(client):
    create_response = client.post("/tasks", json=task_payload(tags=["work"]))
    task_id = create_response.json()["id"]
    response = client.patch(f"/tasks/{task_id}", json={"tags": ["urgent", "personal"]})
    assert response.status_code == 200
    assert sorted(response.json()["tags"]) == ["personal", "urgent"]


def test_update_task_not_found(client):
    response = client.patch("/tasks/999", json={"title": "Nope"})
    assert response.status_code == 404


# ---- DELETE /tasks/{id} ----

def test_delete_task_soft(client):
    create_response = client.post("/tasks", json=task_payload())
    task_id = create_response.json()["id"]

    # Delete
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204

    # Should not appear in list
    list_response = client.get("/tasks")
    assert list_response.json()["total"] == 0

    # Should return 404 on get
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404


def test_delete_task_not_found(client):
    response = client.delete("/tasks/999")
    assert response.status_code == 404
