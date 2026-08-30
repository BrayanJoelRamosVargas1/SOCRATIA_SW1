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
from app.integrations.llm import (
    GeneratedPresentation,
    GeneratedQuestion,
    GeneratedQuestionBank,
    GeneratedSlide,
    PresentationGenerationRequest,
    QuestionCategory,
    QuestionDifficulty,
    QuestionGenerationProviderError,
    QuestionGenerationRequest,
)
from app.integrations.llm.dependencies import (
    get_presentation_generation_router,
    get_question_generation_router,
)
from app.integrations.llm.presentation import slide_count_range
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.llm.router import QuestionGenerationRouter
from app.integrations.storage.dependencies import get_storage_provider
from app.integrations.storage.local import LocalStorageProvider
from app.integrations.vector_db.base import (
    VectorFilter,
    VectorMatch,
    VectorRecord,
    VectorStoreError,
)
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
from app.modules.p2_gestion_documentos_preparacion.models import (
    document,  # noqa: F401
    presentation_material,  # noqa: F401
    question_bank,  # noqa: F401
)


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
        self.queries: list[str] = []
        self.fail = False

    def embed_documents(self, documents: list[EmbeddingDocument]) -> list[list[float]]:
        if self.fail:
            raise EmbeddingError("simulated embedding failure")
        self.documents.extend(documents)
        return [[float(index + 1), 0.5, 0.25] for index, _ in enumerate(documents)]

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        if self.fail:
            raise EmbeddingError("simulated embedding failure")
        self.queries.extend(queries)
        return [[float(index + 1), 0.25, 0.5] for index, _ in enumerate(queries)]


class FakeVectorStoreProvider:
    def __init__(self) -> None:
        self.namespaces: dict[str, dict[str, VectorRecord]] = {}
        self.fail_upsert = False
        self.fail_delete = False
        self.fail_query = False
        self.query_calls: list[dict[str, object]] = []

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

    def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        filters: VectorFilter,
    ) -> list[VectorMatch]:
        if self.fail_query:
            raise VectorStoreError("simulated vector query failure")
        self.query_calls.append(
            {
                "namespace": namespace,
                "vector": vector,
                "top_k": top_k,
                "filters": filters,
            }
        )
        records = list(self.namespaces.get(namespace, {}).values())
        expected = self._equality_filters(filters)
        filtered = [
            record
            for record in records
            if all(record.metadata.get(key) == value for key, value in expected.items())
        ]
        return [
            VectorMatch(id=record.id, score=1 - index * 0.01, metadata=record.metadata)
            for index, record in enumerate(filtered[:top_k])
        ]

    @staticmethod
    def _equality_filters(filters: VectorFilter) -> dict[str, object]:
        clauses = filters.get("$and", [])
        result: dict[str, object] = {}
        if not isinstance(clauses, list):
            return result
        for clause in clauses:
            if not isinstance(clause, dict):
                continue
            for key, expression in clause.items():
                if isinstance(expression, dict) and "$eq" in expression:
                    result[key] = expression["$eq"]
        return result


class FakeQuestionGenerationProvider:
    def __init__(self, *, name: str, model: str) -> None:
        self.name = name
        self.model = model
        self.requests: list[QuestionGenerationRequest] = []
        self.failure: QuestionGenerationProviderError | None = None
        self.invalid_source = False

    def generate(self, request: QuestionGenerationRequest) -> GeneratedQuestionBank:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        chunk_ids = [chunk.id for chunk in request.chunks]
        source_id = "foreign-document:0" if self.invalid_source else chunk_ids[0]
        categories = [category for category in QuestionCategory for _ in range(3)]
        return GeneratedQuestionBank(
            questions=[
                GeneratedQuestion(
                    question=(
                        f"Pregunta academica numero {position + 1}: explique y defienda "
                        "la evidencia recuperada del documento."
                    ),
                    category=category,
                    difficulty=(
                        QuestionDifficulty.MEDIUM
                        if position % 2 == 0
                        else QuestionDifficulty.HARD
                    ),
                    source_chunk_ids=[source_id],
                    expected_answer_points=[
                        "Relacion directa con la evidencia citada",
                        "Justificacion clara de la decision academica",
                    ],
                )
                for position, category in enumerate(categories)
            ]
        )


class FakePresentationGenerationProvider:
    def __init__(self, *, name: str, model: str) -> None:
        self.name = name
        self.model = model
        self.requests: list[PresentationGenerationRequest] = []
        self.failure: QuestionGenerationProviderError | None = None
        self.invalid_source = False

    def generate(self, request: PresentationGenerationRequest) -> GeneratedPresentation:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        minimum, maximum = slide_count_range(request.duration_minutes)
        count = round((minimum + maximum) / 2)
        total_seconds = request.duration_minutes * 60
        seconds, remainder = divmod(total_seconds, count)
        source_id = "foreign:chunk" if self.invalid_source else request.chunks[0].id
        return GeneratedPresentation(
            title=f"Defensa de {request.document_name}",
            total_duration_minutes=request.duration_minutes,
            target_word_count=request.target_word_count,
            slides=[
                GeneratedSlide(
                    position=position,
                    title=f"Seccion academica {position}",
                    objective=f"Explicar la evidencia central de la seccion {position}",
                    bullet_points=["Evidencia principal", "Decision sustentada"],
                    speaker_notes=(
                        "Explica la relacion entre el documento y esta decision academica."
                    ),
                    estimated_seconds=seconds + (1 if position <= remainder else 0),
                    source_chunk_ids=[source_id],
                )
                for position in range(1, count + 1)
            ],
        )


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
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
def question_primary() -> FakeQuestionGenerationProvider:
    return FakeQuestionGenerationProvider(name="gemini", model="fake-gemini")


@pytest.fixture
def question_fallback() -> FakeQuestionGenerationProvider:
    return FakeQuestionGenerationProvider(name="groq", model="fake-groq")


@pytest.fixture
def question_router(
    question_primary: FakeQuestionGenerationProvider,
    question_fallback: FakeQuestionGenerationProvider,
) -> QuestionGenerationRouter:
    return QuestionGenerationRouter(
        primary=question_primary,
        fallback=question_fallback,
        failure_threshold=3,
        recovery_seconds=60,
    )


@pytest.fixture
def presentation_primary() -> FakePresentationGenerationProvider:
    return FakePresentationGenerationProvider(name="gemini", model="fake-gemini")


@pytest.fixture
def presentation_fallback() -> FakePresentationGenerationProvider:
    return FakePresentationGenerationProvider(name="groq", model="fake-groq")


@pytest.fixture
def presentation_router(
    presentation_primary: FakePresentationGenerationProvider,
    presentation_fallback: FakePresentationGenerationProvider,
) -> PresentationGenerationRouter:
    return PresentationGenerationRouter(
        primary=presentation_primary,
        fallback=presentation_fallback,
        failure_threshold=3,
        recovery_seconds=60,
    )


@pytest.fixture
def client(
    db_session: Session,
    storage_provider: LocalStorageProvider,
    email_provider: FakeEmailProvider,
    embedding_provider: FakeEmbeddingProvider,
    vector_store: FakeVectorStoreProvider,
    question_router: QuestionGenerationRouter,
    presentation_router: PresentationGenerationRouter,
) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_provider] = lambda: storage_provider
    app.dependency_overrides[get_email_provider] = lambda: email_provider
    app.dependency_overrides[get_embedding_provider] = lambda: embedding_provider
    app.dependency_overrides[get_vector_store_provider] = lambda: vector_store
    app.dependency_overrides[get_question_generation_router] = lambda: question_router
    app.dependency_overrides[get_presentation_generation_router] = lambda: presentation_router
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
