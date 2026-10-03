import hashlib

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.integrations.embeddings.coordinator import EmbeddingCoordinator
from app.integrations.storage.local import LocalStorageProvider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    ChunkSet,
    DocumentChunk,
    DocumentStatus,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_processing_service import (
    DocumentProcessingService,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_service import DocumentService
from tests.conftest import FakeEmbeddingProvider, FakeVectorStoreProvider


def test_fingerprint_change_prevents_chunk_reuse():
    # Setup test env
    db = SessionLocal()
    user = db.query(User).filter_by(email="smoke-test@example.com").first()
    if not user:
        user = User(email="smoke-test@example.com", full_name="Smoke Test", password_hash="xxx")
        db.add(user)
        db.commit()
        db.refresh(user)

    storage = LocalStorageProvider(root=get_settings().local_storage_path)
    gemini = FakeEmbeddingProvider()
    coordinator = EmbeddingCoordinator(providers=[gemini])
    vectors = FakeVectorStoreProvider()

    doc_service = DocumentService(db=db, storage=storage, vectors=vectors)
    processing_service = DocumentProcessingService(
        db=db, storage=storage, embeddings=coordinator, vectors=vectors
    )

    # We monkeypatch the extractor so we don't really extract a PDF but just return text
    processing_service.extractor.extract = lambda file_type, content: (
        "This is a dummy text that is long enough to be split if the chunk size is very small. We will test this."
    )

    # Mock file
    class MockUploadFile:
        class FakeFile:
            def __init__(self, c):
                self.c = b"%PDF-1.4 " + c
                self.pos = 0

            def read(self, size=-1):
                if size < 0:
                    ret = self.c[self.pos :]
                    self.pos = len(self.c)
                    return ret
                ret = self.c[self.pos : self.pos + size]
                self.pos += size
                return ret

            def seek(self, offset, whence=0):
                if whence == 0:
                    self.pos = offset
                elif whence == 2:
                    self.pos = len(self.c) + offset

            def tell(self):
                return self.pos

        def __init__(self, filename, content=b"Hello world. This is a test file for chunking."):
            self.filename = filename
            self.content_type = "application/pdf"
            self._content = content
            self.file = self.FakeFile(content)

        async def read(self):
            return self._content

    file_v1 = MockUploadFile("fingerprint_test.pdf", b"Hello world v1")
    doc = doc_service.upload(user, file_v1)

    # --- INITIAL RUN ---
    processing_service.settings.document_chunk_size_chars = 3000
    processing_service.settings.document_chunk_overlap_chars = 400
    processing_service.process(user, doc.id)

    db.refresh(doc)
    assert doc.status == DocumentStatus.PROCESSED

    chunk_sets = (
        db.query(ChunkSet).filter_by(document_id=doc.id).order_by(ChunkSet.created_at).all()
    )
    assert len(chunk_sets) == 1
    first_chunk_set = chunk_sets[0]

    first_chunks = db.query(DocumentChunk).filter_by(chunk_set_id=first_chunk_set.id).all()
    first_chunk_count = len(first_chunks)
    assert first_chunk_count > 0

    # --- CASE A: Same content, same config -> Resume ---
    job = processing_service.processing.get_job(doc.id)
    job.chunks_embedded = 0  # force resume from 0
    doc.status = DocumentStatus.UPLOADED
    db.commit()

    processing_service.process(user, doc.id)

    chunk_sets = (
        db.query(ChunkSet).filter_by(document_id=doc.id).order_by(ChunkSet.created_at).all()
    )
    assert len(chunk_sets) == 1, "Should reuse existing chunk set (CASE A)"
    assert chunk_sets[0].id == first_chunk_set.id

    # --- CASE B: Same content, different config -> New ChunkSet ---
    job.chunks_embedded = 0
    doc.status = DocumentStatus.UPLOADED
    db.commit()

    processing_service.settings.document_chunk_size_chars = 10
    processing_service.settings.document_chunk_overlap_chars = 2

    processing_service.process(user, doc.id)

    chunk_sets = (
        db.query(ChunkSet).filter_by(document_id=doc.id).order_by(ChunkSet.created_at).all()
    )
    assert len(chunk_sets) == 2, "Should create new chunk set due to config change (CASE B)"
    second_chunk_set = chunk_sets[1]
    assert first_chunk_set.fingerprint != second_chunk_set.fingerprint

    # --- CASE C: Different content, same config as v2 -> New ChunkSet ---
    # To change content, we simulate replacing the file on the document and updating content_hash
    new_content = b"This is a completely different file content for v2"
    new_hash = hashlib.sha256(new_content).hexdigest()
    doc.content_hash = new_hash
    job.chunks_embedded = 0
    doc.status = DocumentStatus.UPLOADED
    db.commit()

    processing_service.process(user, doc.id)

    chunk_sets = (
        db.query(ChunkSet).filter_by(document_id=doc.id).order_by(ChunkSet.created_at).all()
    )
    assert len(chunk_sets) == 3, "Should create new chunk set due to content hash change (CASE C)"
    third_chunk_set = chunk_sets[2]
    assert second_chunk_set.fingerprint != third_chunk_set.fingerprint

    # Assert active profile points to the newest chunk set
    db.refresh(doc)
    active_profile = next(
        p for p in doc.embedding_profiles if p.id == doc.active_embedding_profile_id
    )
    assert active_profile.chunk_set_id == third_chunk_set.id, (
        "Active profile should point to newest chunk set"
    )

    print("Test passed! 3 cases verified.")
