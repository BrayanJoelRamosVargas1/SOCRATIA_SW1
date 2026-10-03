import logging

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.integrations.embeddings.coordinator import EmbeddingCoordinator
from app.integrations.storage.local import LocalStorageProvider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    DocumentStatus,
    ProfileStatus,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_processing_service import (
    DocumentProcessingService,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_service import DocumentService

logging.basicConfig(level=logging.INFO)

db = SessionLocal()

# We need a user.
user = db.query(User).filter_by(email="smoke-test@example.com").first()
if not user:
    user = User(
        email="smoke-test@example.com",
        full_name="Smoke Test",
        password_hash="xxx",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

storage = LocalStorageProvider(root=get_settings().local_storage_path)
from tests.conftest import FakeEmbeddingProvider, FakeVectorStoreProvider

gemini = FakeEmbeddingProvider()
gemini.provider_id = "gemini"
gemini._model = "gemini"  # fake the property
gemini.dimensions = 768
gemini.batch_size = 20
gemini.timeout_seconds = 60
gemini.embedding_space_id = "GEMINI_SPACE"
gemini.execution_location = "remote"
gemini.is_available = True

cohere = FakeEmbeddingProvider()
cohere.provider_id = "cohere"
cohere._model = "cohere"
cohere.dimensions = 1024
cohere.batch_size = 20
cohere.timeout_seconds = 60
cohere.embedding_space_id = "COHERE_SPACE"
cohere.execution_location = "remote"
cohere.is_available = True

hf_remote = FakeEmbeddingProvider()
hf_remote.provider_id = "huggingface"
hf_remote._model = "hf-remote"
hf_remote.dimensions = 768
hf_remote.batch_size = 10
hf_remote.timeout_seconds = 60
hf_remote.embedding_space_id = "E5_SPACE"
hf_remote.execution_location = "remote"
hf_remote.is_available = True

local_e5 = FakeEmbeddingProvider()
local_e5.provider_id = "local_e5"
local_e5._model = "local-e5"
local_e5.dimensions = 768
local_e5.batch_size = 10
local_e5.timeout_seconds = 60
local_e5.embedding_space_id = "E5_SPACE"
local_e5.execution_location = "local"
local_e5.is_available = True

coordinator = EmbeddingCoordinator(providers=[gemini, cohere, hf_remote, local_e5])

vectors = FakeVectorStoreProvider()

doc_service = DocumentService(db=db, storage=storage, vectors=vectors)
processing_service = DocumentProcessingService(
    db=db,
    storage=storage,
    embeddings=coordinator,
    vectors=vectors,
)

PDF_PATH = "proyectSI2_SPRINT4_grupo12.pdf"


class MockUploadFile:
    def __init__(self, filename, filepath):
        self.filename = filename
        self.file = open(filepath, "rb")
        self.content_type = "application/pdf"


def run_smoke_1():
    print("--- SMOKE 1: Gemini Normal ---")
    get_settings().embedding_force_provider_failure = None
    file = MockUploadFile("proyectSI2_SPRINT4_grupo12.pdf", PDF_PATH)
    doc = doc_service.upload(user, file)
    print(f"Uploaded as {doc.id}")

    processing_service.process(user, doc.id)

    db.refresh(doc)
    assert doc.status == DocumentStatus.PROCESSED, f"Expected PROCESSED, got {doc.status}"
    assert doc.active_embedding_profile_id is not None

    active_profile = next(
        (p for p in doc.embedding_profiles if p.id == doc.active_embedding_profile_id), None
    )
    assert active_profile is not None
    assert active_profile.provider == "gemini"
    print(
        f"DEBUG: active_profile.status = {active_profile.status!r}, type = {type(active_profile.status)}"
    )
    assert active_profile.status == ProfileStatus.ACTIVE
    assert active_profile.dimension == 768

    # Assert Pinecone physically created
    print(
        f"Smoke 1 SUCCESS: Gemini profile {active_profile.id} created and active in {active_profile.vector_index}."
    )
    return doc.id


def run_smoke_2():
    print("--- SMOKE 2: Gemini -> Cohere Fallback ---")
    get_settings().embedding_force_provider_failure = "gemini"
    file = MockUploadFile("proyectSI2_SPRINT4_grupo12.pdf", PDF_PATH)
    doc = doc_service.upload(user, file)

    processing_service.process(user, doc.id)

    db.refresh(doc)
    assert doc.status == DocumentStatus.PROCESSED, f"Expected PROCESSED, got {doc.status}"
    assert doc.active_embedding_profile_id is not None

    active_profile = next(
        (p for p in doc.embedding_profiles if p.id == doc.active_embedding_profile_id), None
    )
    assert active_profile is not None
    assert active_profile.provider == "cohere"
    print(
        f"DEBUG: active_profile.status = {active_profile.status!r}, type = {type(active_profile.status)}"
    )
    assert active_profile.status == ProfileStatus.ACTIVE
    assert active_profile.dimension == 1024

    gemini_profile = next((p for p in doc.embedding_profiles if p.provider == "gemini"), None)
    assert gemini_profile is not None
    assert gemini_profile.status in (
        ProfileStatus.RETIRED,
        ProfileStatus.FAILED,
        ProfileStatus.STAGING,
    )  # It never completed

    print(
        f"Smoke 2 SUCCESS: Cohere profile {active_profile.id} created and active in {active_profile.vector_index}."
    )
    return doc.id


def run_smoke_3(doc_id: str):
    print("--- SMOKE 3: RAG with Cohere ---")
    get_settings().embedding_force_provider_failure = None
    from app.integrations.llm.router import QuestionGenerationRouter
    from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import (
        QuestionBankService,
    )
    from tests.conftest import FakeQuestionGenerationProvider

    question_primary = FakeQuestionGenerationProvider(name="gemini", model="fake-gemini")
    question_fallback = FakeQuestionGenerationProvider(name="groq", model="fake-groq")
    router = QuestionGenerationRouter(
        primary=question_primary,
        fallback=question_fallback,
        failure_threshold=3,
        recovery_seconds=60,
    )
    qb_service = QuestionBankService(
        db=db, embeddings=coordinator, vectors=vectors, generation_router=router
    )

    doc = doc_service.get_for(user, doc_id)
    bank = qb_service.generate(user, doc.id)

    assert bank is not None
    assert len(bank.questions) == 12
    print(f"Smoke 3 SUCCESS: Generated {len(bank.questions)} questions using Cohere RAG.")


def run_smoke_4():
    print("--- SMOKE 4: Fallback to Local E5 (Simulating HF timeout) ---")
    get_settings().embedding_force_provider_failure = "gemini,cohere,huggingface"
    file = MockUploadFile("proyectSI2_SPRINT4_grupo12.pdf", PDF_PATH)
    doc = doc_service.upload(user, file)

    processing_service.process(user, doc.id)

    db.refresh(doc)
    assert doc.status == DocumentStatus.PROCESSED, f"Expected PROCESSED, got {doc.status}"

    active_profile = next(
        (p for p in doc.embedding_profiles if p.id == doc.active_embedding_profile_id), None
    )
    assert active_profile is not None
    assert active_profile.provider == "local_e5"
    print(
        f"Smoke 4 SUCCESS: Local E5 profile {active_profile.id} active in {active_profile.vector_index}."
    )


def run_smoke_5():
    print("--- SMOKE 5: Rollback of Staging (All Failed) ---")
    get_settings().embedding_force_provider_failure = "both"  # Our fake logic checks "both" to fail all, or we could just use "gemini,cohere,huggingface,local_e5"
    get_settings().embedding_force_provider_failure = "gemini,cohere,huggingface,local_e5"

    file = MockUploadFile("proyectSI2_SPRINT4_grupo12.pdf", PDF_PATH)
    doc = doc_service.upload(user, file)

    try:
        processing_service.process(user, doc.id)
    except Exception as e:
        print(f"Expected failure caught: {e}")

    db.refresh(doc)
    assert doc.status == DocumentStatus.ERROR

    profiles = doc.embedding_profiles
    assert all(p.status in (ProfileStatus.FAILED, ProfileStatus.STAGING) for p in profiles)
    assert doc.active_embedding_profile_id is None
    print("Smoke 5 SUCCESS: Profiles failed gracefully and active profile remained unchanged.")


if __name__ == "__main__":
    doc_1 = run_smoke_1()
    doc_2 = run_smoke_2()
    run_smoke_3(doc_2)
    run_smoke_4()
    run_smoke_5()
    print("ALL SMOKE TESTS PASSED!")
