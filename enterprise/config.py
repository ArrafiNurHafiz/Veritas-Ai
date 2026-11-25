"""Engine and session configuration for the VERITAS AI enterprise data layer.

The connection string comes exclusively from ``DATABASE_URL``. Postgres URLs are
normalised to the psycopg 3 driver; SQLite remains supported for local tests.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite:///./enterprise.db"


def get_database_url() -> str:
    """Return the effective DATABASE_URL, normalised for psycopg 3."""
    url = (os.environ.get("DATABASE_URL") or "").strip() or DEFAULT_DATABASE_URL
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def is_sqlite(url: str | None = None) -> bool:
    return (url or get_database_url()).startswith("sqlite")


def create_database_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    """Build an Engine for the resolved URL (SQLite or Postgres/psycopg 3)."""
    resolved = url or get_database_url()
    options: dict[str, object] = {"echo": echo, "future": True}
    if resolved.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in resolved:
            # One connection for the whole in-memory database, otherwise every
            # pooled connection would see a different empty database.
            options["poolclass"] = StaticPool
        engine = create_engine(resolved, **options)

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    options.update(pool_pre_ping=True, pool_size=5, max_overflow=10)
    return create_engine(resolved, **options)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Process-wide engine, created lazily from the current environment."""
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine


def reset_engine() -> None:
    """Dispose cached engine/factory (tests that switch DATABASE_URL)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
            class_=Session,
        )
    return _session_factory


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    """Transactional session context that commits on success, rolls back on error."""
    factory = (
        sessionmaker(
            bind=create_database_engine(url),
            expire_on_commit=False,
            autoflush=False,
            class_=Session,
        )
        if url
        else get_session_factory()
    )
    session = factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine | None = None) -> None:
    """Create tables from ORM metadata (local dev / tests; Alembic owns prod)."""
    from .models import Base

    Base.metadata.create_all(bind=engine or get_engine())
