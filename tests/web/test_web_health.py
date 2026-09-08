"""Liveness/readiness probes, and how an unreachable database is reported.

Regression cover for the case where the process is up but Postgres is not: the
authenticated endpoints used to raise a bare ``ConnectionRefusedError`` out of
asyncpg, which FastAPI turned into an empty ``500 Internal Server Error`` -- so
the browser console showed "Internal Server Error" with no clue that the
database was simply down, and ``/health`` cheerfully reported ``ok`` throughout.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from artificial_writer.service import db as service_db


@pytest.fixture
def unreachable_db_client(tmp_path: Path) -> Iterator[TestClient]:
    """A TestClient whose engine points at a database that cannot be opened.

    Uses SQLite under a directory that does not exist, which fails the same way
    a dead Postgres does (a connect-time error, not a query error) without
    needing a network port or a driver beyond the test deps.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from artificial_writer.web.app import app

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'missing-dir' / 'test.db'}",
        poolclass=NullPool,
    )
    service_db.configure_engine(engine)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        asyncio.run(engine.dispose())
        service_db.reset_engine()


def test_health_is_shallow(unreachable_db_client: TestClient) -> None:
    # Liveness must not depend on the database: the process is serving fine.
    resp = unreachable_db_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_reports_unavailable_database(unreachable_db_client: TestClient) -> None:
    resp = unreachable_db_client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not ready"
    assert body["database"] == "unavailable"
    assert body["detail"]  # carries the underlying reason, not an empty string


def test_ready_succeeds_against_a_live_database(service_client: TestClient) -> None:
    resp = service_client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "database": "ok"}


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/auth/login", {"email": "a@example.com", "password": "password123"}),
        ("/auth/register", {"email": "a@example.com", "password": "password123"}),
    ],
)
def test_db_backed_endpoints_return_503_not_500(
    unreachable_db_client: TestClient, path: str, payload: dict
) -> None:
    """A dead database is a 503 with a message, never an opaque 500."""
    resp = unreachable_db_client.post(path, json=payload)

    assert resp.status_code == 503
    assert resp.headers["Retry-After"] == "5"
    assert "Database unavailable" in resp.json()["detail"]


def test_credential_lookup_reports_503(unreachable_db_client: TestClient) -> None:
    """The auth dependency surfaces a dead database too, rather than a 500.

    A *credential-less* request is still a plain 401 -- ``current_user`` rejects
    it before any query -- so this sends a bearer token to force the API-key
    lookup that actually touches the database.
    """
    resp = unreachable_db_client.get(
        "/auth/me", headers={"Authorization": "Bearer aw_nonexistent"}
    )
    assert resp.status_code == 503
    assert "Database unavailable" in resp.json()["detail"]


def test_missing_credentials_still_401(unreachable_db_client: TestClient) -> None:
    # The database being down must not turn an unauthenticated call into a 503.
    assert unreachable_db_client.get("/auth/me").status_code == 401


def test_unreachable_message_masks_the_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """The 503 detail names the database it tried, but never leaks credentials."""
    from artificial_writer.core.config import Settings

    settings = Settings(database_url="postgresql+asyncpg://aw:hunter2@db:5432/aw")
    monkeypatch.setattr(service_db, "get_settings", lambda: settings)

    message = service_db._unreachable_message(ConnectionRefusedError("refused"))

    assert "hunter2" not in message
    assert "db:5432" in message
    assert "refused" in message
