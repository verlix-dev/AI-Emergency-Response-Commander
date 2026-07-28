import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db_session
from app.main import app
import app.models  # noqa: F401


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    database_session = factory()
    try:
        yield database_session
    finally:
        database_session.close(); Base.metadata.drop_all(engine)


@pytest.fixture()
def client(session: Session) -> TestClient:
    def override_session():
        yield session
    app.dependency_overrides[get_db_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
