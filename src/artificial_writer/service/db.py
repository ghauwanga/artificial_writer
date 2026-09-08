"""Async SQLAlchemy engine, session factory, and the FastAPI session dependency.

The engine is created lazily so this module stays importable without a live
database (importing it never opens a connection). Tests swap in a SQLite engine
via :func:`configure_engine`; production reads ``settings.database_url``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from ..core.config import get_settings
from ..core.errors import StorageUnavailable


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model in this package."""


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, creating it on first use."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


def configure_engine(engine: AsyncEngine) -> None:
    """Install an explicit engine (and matching sessionmaker).

    Used by tests to point the session dependency at an in-memory SQLite
    database without going through ``settings.database_url``.
    """
    global _engine, _sessionmaker
    _engine = engine
    _sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


def reset_engine() -> None:
    """Forget the cached engine/sessionmaker (mainly for test isolation)."""
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None


# Connectivity failures, as opposed to caller mistakes. asyncpg raises a bare
# ``OSError`` (e.g. ConnectionRefusedError) when the server is not listening --
# SQLAlchemy never wraps it, because OSError is not a DBAPI ``Error`` -- so it
# has to be caught alongside SQLAlchemy's own connect/disconnect errors.
# ``IntegrityError``/``ProgrammingError`` are deliberately excluded: those mean
# the code or schema is wrong, and should stay loud 500s rather than be
# mislabelled as "the database is down".
_UNREACHABLE = (OSError, InterfaceError, OperationalError)


def _safe_url() -> str:
    """Return the configured database URL with any password masked."""
    try:
        return make_url(get_settings().database_url).render_as_string(hide_password=True)
    except Exception:  # pragma: no cover - a malformed URL must not mask the real error
        return "the configured database"


def _unreachable_message(exc: BaseException) -> str:
    return f"Database unavailable at {_safe_url()}: {exc}"


async def check_connection() -> str | None:
    """Ping the database; return ``None`` if it answers, else a short reason.

    Used by the readiness probe so a live process with a dead database reports
    itself as not-ready instead of claiming to be healthy.
    """
    try:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - the probe reports, never raises
        return _unreachable_message(exc)
    return None


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an :class:`AsyncSession`.

    Failures to reach the database are re-raised as
    :class:`~...core.errors.StorageUnavailable` so front-ends can return a 503
    with an actionable message instead of an empty 500.
    """
    try:
        async with get_sessionmaker()() as session:
            yield session
    except _UNREACHABLE as exc:
        raise StorageUnavailable(_unreachable_message(exc)) from exc
