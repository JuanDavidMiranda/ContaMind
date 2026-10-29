import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database = tmp_path / "test.db"
    storage = tmp_path / "storage"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database.as_posix()}")
    monkeypatch.setenv("STORAGE_DIR", str(storage))
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_USER_EMAIL", "dev@contamind.local")
    monkeypatch.setenv("DEV_USER_NAME", "Usuario local de desarrollo")

    from app.core.config import get_settings
    from app.db.base import Base
    from app.db.session import get_engine, reset_engine
    import app.db.models  # noqa: F401

    get_settings.cache_clear()
    reset_engine()
    Base.metadata.create_all(get_engine())

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    reset_engine()
    get_settings.cache_clear()
