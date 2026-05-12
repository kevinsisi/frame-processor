# Design — Backend Integration Test Harness

## Decision required: DB backend

Three candidates:

### Option A — testcontainers Postgres 16 (recommended)

```python
# tests/conftest.py
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg
```

Pros:
- Same Postgres version, JSONB, ARRAY, enum types as production. Zero behavioral drift.
- Alembic migrations run against the same dialect — `0007_batch_versions` migration tests are meaningful.
- testcontainers handles Docker lifecycle; works on CI runners that already have Docker (kevinhome runner does).

Cons:
- Adds `testcontainers[postgres]` dependency.
- Container startup ~3-5s per test session. Acceptable since per-test uses transaction rollback, not container restart.
- Requires Docker on contributor machines. Already a project requirement (deploy stack).

### Option B — sqlite + compatibility shim

```python
# Replace JSONB → JSON, ARRAY(UUID) → JSON-of-strings, SAEnum → CHECK constraint
```

Pros:
- No Docker required for tests.
- Fast startup.

Cons:
- Significant dialect drift: ARRAY operators, `with_for_update`, JSONB containment operators (`->`, `?`, `@>`) all behave differently. Real bugs in production can pass sqlite tests (the exact category we are trying to catch).
- Every new Postgres-only feature requires shim maintenance.
- Migration tests are basically untestable — alembic generates Postgres DDL.

### Option C — pytest-docker / docker compose

Pros:
- Matches production exactly.

Cons:
- pytest-docker is finicky on Windows where the dev environment lives.
- testcontainers-python is the standard equivalent of Option C with a cleaner Python API.

**Decision**: **Option A — testcontainers Postgres**. The whole point of the harness is to catch Postgres-specific behavior; sqlite shim defeats the purpose. Container overhead is fine.

## Fixture shape

### `db_session`

```python
@pytest.fixture
def db_session(postgres_container) -> Iterator[Session]:
    # Reuse a session-scoped engine; per-test transaction with rollback.
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
```

`get_db` dependency override in the TestClient points to this same session so a route handler and the assertion code share state.

### `client`

```python
@pytest.fixture
def client(db_session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

### `fake_queue`

A drop-in replacement for `api.queue.default_queue` that records calls without running them:

```python
class FakeQueue:
    def __init__(self):
        self.enqueued: list[tuple[str, tuple, dict]] = []
    def enqueue(self, func_name, *args, **kwargs):
        self.enqueued.append((func_name, args, kwargs))
        return SimpleNamespace(id=str(uuid.uuid4()))
```

Worker-side tests can call `worker.jobs.process_photo_version_job(...)` directly to verify behavior without an actual RQ worker process.

### Factories (replace inline `_make_*`)

```python
@pytest.fixture
def make_project(db_session):
    def _make(name="test") -> Project:
        proj = Project(name=name)
        db_session.add(proj)
        db_session.commit()
        return proj
    return _make

# similar make_photo, make_processing_job, make_photo_processing_version
```

## Worker integration testing

```python
def test_process_photo_version_writes_immutable_batch_path(
    db_session, make_project, make_photo, make_processing_job, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    project = make_project()
    photo = make_photo(project, with_test_image=True)
    job = make_processing_job(project, photo_ids=[photo.id], version_number=1)

    process_photo_version_job(str(job.id), str(photo.id))

    expected = tmp_path / "projects" / str(project.id) / "processed" / f"{photo.id}.batch-v1.jpg"
    assert expected.exists()
    row = db_session.get(PhotoProcessingVersion, ...)
    assert row.status == "done"
    assert row.path.endswith(".batch-v1.jpg")
```

The synthetic image is a 64×64 noise patch — enough for the pipeline to run without taking minutes.

## CI wiring

`.github/workflows/ci.yml` already runs lint and an import smoke. Extend it:

```yaml
- name: Set up Docker (testcontainers needs it)
  uses: docker/setup-buildx-action@v3
- name: Run tests
  run: pytest -q
```

GitHub-hosted runners include Docker by default. The kevinhome self-hosted runner has Docker (deployments run on it).

## Migration testing approach

```python
def test_alembic_0007_initial_version_numbering(alembic_runner, db_session):
    alembic_runner.migrate_up_to("0006_adjustment_versions")
    # insert pre-batch-versioning processing_jobs row
    alembic_runner.migrate_up_to("0007_batch_versions")
    # assert version_number column populated with monotonic 1..N per project
```

Use `pytest-alembic` (small dependency) to step migrations.

## Out of scope

- Async fixtures (FastAPI sync routes don't need them).
- Property-based testing (Hypothesis) — independent decision.
- Coverage thresholds — separate change once baseline is established.
- Frontend test infrastructure beyond the existing `.cjs` sandboxes.
