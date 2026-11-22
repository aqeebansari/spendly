import pytest

from database import db as db_module


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Fresh, initialised (unseeded) database in a temp file."""
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init_db()
    conn = db_module.get_db()
    yield conn
    conn.close()
