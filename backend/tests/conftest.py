import os

os.environ["FIRE_DISABLE_SCHEDULER"] = "1"

import pytest
from fastapi.testclient import TestClient

from app import database, fetcher, main


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "fire.db"
    database.configure(path)
    database.init_db()
    return path


@pytest.fixture()
def db(db_path):
    with database.SessionLocal() as s:
        yield s


@pytest.fixture()
def client(db_path, monkeypatch):
    monkeypatch.setattr(fetcher, "normalize_symbol", lambda raw: {"0050": "0050.TW"}.get(raw, raw.upper()))
    monkeypatch.setattr(fetcher, "lookup_name", lambda s: s)
    monkeypatch.setattr(main, "refresh_in_background", lambda *a, **k: None)
    with TestClient(main.app) as c:
        yield c
