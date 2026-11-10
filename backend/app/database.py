"""SQLite connection and schema initialisation."""
from __future__ import annotations

import os
import threading
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = Path(os.environ.get("FIRE_DB_PATH", "./data/fire.db"))


class Base(DeclarativeBase):
    pass


def _make_engine(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    eng = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn, _):  # pragma: no cover - trivial
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return eng


engine = _make_engine(DB_PATH)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# All writes that rebuild derived tables go through this lock so the scheduler
# thread and API requests never rebuild at the same time.
write_lock = threading.RLock()


def configure(path: str | Path) -> None:
    """Point the app at another database file (used by tests)."""
    global engine
    engine = _make_engine(Path(path))
    SessionLocal.configure(bind=engine)


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        models.ensure_defaults(db)
        db.commit()
    _migrate()


def _migrate() -> None:
    """One-off data migrations, tracked with SQLite's user_version."""
    with engine.begin() as conn:
        version = conn.exec_driver_sql("PRAGMA user_version").scalar() or 0
        if version < 1:
            # The campfire redesign made "ember" the default theme. Databases that
            # still have the old default "teal" move to it once; a later manual
            # switch back to teal is kept.
            conn.exec_driver_sql("UPDATE game_settings SET theme = 'ember' WHERE theme = 'teal'")
            conn.exec_driver_sql("PRAGMA user_version = 1")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
