from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.integrations.email.base import OutboundEmail
from app.integrations.email.dependencies import get_email_provider
from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError
from app.integrations.embeddings.dependencies import get_embedding_provider
from app.integrations.storage.dependencies import get_storage_provider
from app.integrations.storage.local import LocalStorageProvider
from app.integrations.vector_db.base import VectorRecord, VectorStoreError
from app.integrations.vector_db.dependencies import get_vector_store_provider
from app.main import app
from app.modules.p1_gestion_identidad_seguridad.models import (
    login_security as login_security_models,  # noqa: F401
)
from app.modules.p1_gestion_identidad_seguridad.models import (
    password_reset as password_reset_models,  # noqa: F401
)
from app.modules.p1_gestion_identidad_seguridad.models import (
    session as session_models,  # noqa: F401
)
from app.modules.p1_gestion_identidad_seguridad.models import user as user_models  # noqa: F401
from app.modules.p2_gestion_documentos_preparacion.models import document  # noqa: F401


class FakeEmailProvider:
    def __init__(self) -> None:
        self.messages: list[OutboundEmail] = []

    def send(self, message: OutboundEmail) -> None:
        self.messages.append(message)


class FakeEmbeddingProvider:
    model = "fake-embedding"
    dimensions = 3

    def __init__(self) -> None:
        self.documents: list[EmbeddingDocument] = []
        self.fail = False

    def embed_documents(self, documents: list[EmbeddingDocument]) -> list[list[float]]:
        if self.fail:
            raise EmbeddingError("simulated embedding failure")
        self.documents.extend(documents)
        return [[float(index + 1), 0.5, 0.25] for index, _ in enumerate(documents)]


class FakeVectorStoreProvider:
    def __init__(self) -> None:
        self.namespaces: dict[str, dict[str, VectorRecord]] = {}
        self.fail_upsert = False
        self.fail_delete = False

    def upsert(self, *, namespace: str, records: list[VectorRecord]) -> None:
        if self.fail_upsert:
            raise VectorStoreError("simulated vector failure")
        target = self.namespaces.setdefault(namespace, {})
        target.update({record.id: record for record in records})

    def delete(self, *, namespace: str, ids: list[str]) -> None:
        if self.fail_delete:
            raise VectorStoreError("simulated vector failure")
        target = self.namespaces.setdefault(namespace, {})
        for vector_id in ids:
            target.pop(vector_id, None)


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
def email_provider() -> FakeEmailProvider:
    return FakeEmailProvider()


@pytest.fixture
def embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def vector_store() -> FakeVectorStoreProvider:
    return FakeVectorStoreProvider()


@pytest.fixture
def client(
    db_session: Session,
    storage_provider: LocalStorageProvider,
    email_provider: FakeEmailProvider,
    embedding_provider: FakeEmbeddingProvider,
    vector_store: FakeVectorStoreProvider,
) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_provider] = lambda: storage_provider
    app.dependency_overrides[get_email_provider] = lambda: email_provider
    app.dependency_overrides[get_embedding_provider] = lambda: embedding_provider
    app.dependency_overrides[get_vector_store_provider] = lambda: vector_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
