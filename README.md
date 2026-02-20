# Task Management API

A RESTful Task Management API built with FastAPI, SQLModel, and PostgreSQL. Supports task creation, advanced filtering, tagging, pagination, and soft deletion.

## Tech Stack

- **Language:** Python 3.11
- **Framework:** FastAPI
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Database:** PostgreSQL 15
- **Testing:** pytest + httpx
- **Containerization:** Docker + docker-compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed

### Setup

```bash
cp .env.example .env
```

### Run with Docker (single command)

```bash
docker-compose up --build
```

This starts both services:
- **API** at `http://localhost:8000`
- **PostgreSQL** at `localhost:5433` (port 5433 is used to avoid conflicts with a local PostgreSQL instance on the default port 5432)

### API Documentation

Once running, open the interactive Swagger UI:

```
http://localhost:8000/docs
```

### Run Tests

```bash
uv run pytest tests/ -v
```

Tests use an in-memory SQLite database and do not require PostgreSQL to be running. The test suite uses FastAPI's `TestClient`, which is built on top of `httpx` under the hood, to simulate HTTP requests without starting a real server.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tasks` | Create a new task |
| GET | `/tasks` | List tasks (with filtering and pagination) |
| GET | `/tasks/{id}` | Get a single task |
| PATCH | `/tasks/{id}` | Partial update a task |
| DELETE | `/tasks/{id}` | Soft delete a task |

### Filtering & Pagination (GET /tasks)

| Parameter | Type | Description |
|-----------|------|-------------|
| `completed` | bool | Filter by completion status |
| `priority` | int | Filter by priority level (1-5) |
| `tags` | string | CSV format, e.g. `?tags=work,urgent` |
| `limit` | int | Page size (default: 10) |
| `offset` | int | Skip N results (default: 0) |

### Error Format

All validation errors return a consistent structure:

```json
{
  "error": "Validation Failed",
  "details": {
    "priority": "Input should be less than or equal to 5"
  }
}
```

## Project Structure

```
app/
├── config.py          # Environment config (DATABASE_URL)
├── database.py        # Engine + session dependency
├── models.py          # DB tables + request/response models
├── main.py            # FastAPI app + error handler
└── routers/
    └── tasks.py       # All /tasks endpoints
tests/
    └── test_tasks.py  # 17 test cases
Dockerfile
docker-compose.yml
```

## Design Decisions

### Tagging: Join Table vs. JSONB vs. ARRAY

I chose a **Join Table** (`TaskTagLink`) for the many-to-many relationship between Tasks and Tags.

| Approach | Pros | Cons |
|----------|------|------|
| **Join Table** (chosen) | Normalized, supports efficient querying and indexing, easy to filter by tag, tags are reusable across tasks | Requires JOIN queries, slightly more complex schema |
| **PostgreSQL ARRAY** | Simple schema, no extra table needed | Cannot index individual elements efficiently, no referential integrity, duplicates possible |
| **PostgreSQL JSONB** | Flexible schema, good for unstructured data | Overkill for simple string tags, harder to query and index, no referential integrity |

**Why Join Table:** The API requires filtering tasks by tags (`?tags=work,urgent`), which demands efficient querying. A normalized join table with an indexed `Tag.name` column supports this well. It also enforces uniqueness of tag names and allows tags to be shared across tasks without duplication.

### Soft Delete vs. Hard Delete

I chose **Soft Delete** using a `deleted_at` timestamp field.

**Reasons:**
- **Data recovery:** Accidentally deleted tasks can be restored by clearing the `deleted_at` field.
- **Audit trail:** We retain a record of when a task was deleted.
- **Referential safety:** No risk of cascading deletes breaking related data (e.g., tag associations).
- **Production standard:** Most production systems use soft delete for compliance and debugging purposes.

**Trade-off:** Soft delete requires adding `WHERE deleted_at IS NULL` to all queries, which adds slight complexity. I handle this consistently in the query layer.

### Database Indexes

Indexes are applied to frequently filtered columns:

- `Task.priority`: used in `?priority=` filter
- `Task.completed`: used in `?completed=` filter
- `Tag.name` (unique): used in tag lookup and `?tags=` filter

## Production Readiness Improvements

My primary background is in Node.js/TypeScript, and I have limited experience with FastAPI. However, the core concepts (routing, middleware, dependency injection) are very similar to Express, so the improvements below are based on my Express experience. If anything doesn't quite follow FastAPI conventions, I'm happy to take feedback.

1. **Database Migrations:** Replace `create_all()` with a proper migration tool to support incremental, version-controlled schema changes, similar to how I would use Prisma Migrate or Knex migrations in Node.js.

2. **Authentication & Authorization:** Add token-based authentication (JWT or OAuth2) to protect endpoints. FastAPI has built-in dependency injection support for this, similar to Express middleware.

3. **Rate Limiting:** Add request rate limiting to prevent abuse, the same concept as `express-rate-limit` in Node.js.

4. **Structured Logging:** Replace `print()` statements with a proper logging solution for better observability, filtering, and log levels in production.

5. **Pagination Optimization:** Use a `SELECT COUNT(*)` query for total count instead of loading all rows into memory. This matters at scale.

6. **Health Check Endpoint:** Add a `GET /health` endpoint that verifies database connectivity, useful for load balancers and container orchestration (e.g., Docker, Kubernetes).

7. **Environment Configuration:** Use separate environment configurations for development, staging, and production. Never commit secrets to version control.

8. **CI/CD Pipeline:** Add GitHub Actions to automatically run tests, lint code, and build Docker images on every push.

9. **CORS Configuration:** Configure CORS middleware to restrict which origins can access the API, same concept as the `cors` middleware in Express.

10. **Database Connection Pooling:** Tune connection pool settings for handling concurrent requests efficiently, similar to configuring `pg` pool options in Node.js.
