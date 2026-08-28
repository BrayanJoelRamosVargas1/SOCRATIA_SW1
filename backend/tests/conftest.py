from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.integrations.storage.dependencies import get_storage_provider
from app.integrations.storage.local import LocalStorageProvider
from app.main import app
from app.modules.p1_gestion_identidad_seguridad.models import (
    login_security as login_security_models,  # noqa: F401
)
from app.modules.p1_gestion_identidad_seguridad.models import (
    session as session_models,  # noqa: F401
)
from app.modules.p1_gestion_identidad_seguridad.models import user as user_models  # noqa: F401
from app.modules.p2_gestion_documentos_preparacion.models import document  # noqa: F401


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def storage_provider(tmp_path: Path) -> LocalStorageProvider:
    return LocalStorageProvider(tmp_path / "uploads")


@pytest.fixture
def client(
    db_session: Session,
    storage_provider: LocalStorageProvider,
) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_provider] = lambda: storage_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
