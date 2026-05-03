from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    url = settings.database_url

    if url.startswith("sqlite"):
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.debug,
        )
        # Enable WAL mode and foreign keys for SQLite
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        _engine = create_engine(url, pool_pre_ping=True, echo=settings.debug)

    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def init_db():
    """Create all tables if they don't exist, then apply any additive column migrations."""
    from backend.app.db import models  # noqa: F401 — registers all models
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns(engine)


def _migrate_add_columns(engine) -> None:
    """Idempotently add new columns to existing tables (SQLite-safe ALTER TABLE)."""
    new_cols = [
        # (table, column, ddl_type)
        ("users",       "is_active",           "BOOLEAN DEFAULT 1"),
        ("assessments", "eval_category",      "VARCHAR(20)"),
        ("assessments", "steo_mission_name",   "VARCHAR(255)"),
        ("assessments", "ldr_planning",        "FLOAT"),
        ("assessments", "ldr_atd",             "FLOAT"),
        ("assessments", "ldr_time_mgmt",       "FLOAT"),
        ("assessments", "ldr_decisiveness",    "FLOAT"),
        ("assessments", "ldr_tactics",         "FLOAT"),
        ("assessments", "ump_planning",        "FLOAT"),
        ("assessments", "ump_atd",             "FLOAT"),
        ("assessments", "ump_time_mgmt",       "FLOAT"),
        ("assessments", "ump_decisiveness",    "FLOAT"),
        ("assessments", "ump_tactics",         "FLOAT"),
        # Mission AO / weather context fields
        ("missions", "ao_grid_center",      "VARCHAR(20)"),
        ("missions", "ao_radius_km",        "FLOAT"),
        ("missions", "weather_snapshot_id", "INTEGER"),
    ]
    with engine.connect() as conn:
        for table, col, col_type in new_cols:
            try:
                conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"
                    )
                )
                conn.commit()
            except Exception:
                pass  # column already exists — ignore


def get_db():
    """FastAPI dependency — yields a database session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
