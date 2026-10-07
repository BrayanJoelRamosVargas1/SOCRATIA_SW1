from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    Document,
    DocumentStatus,
    EmbeddingProfile,
)
from app.modules.p2_gestion_documentos_preparacion.models.vector_store import VectorSyncOutbox
from app.modules.p2_gestion_documentos_preparacion.services.document_service import DocumentService
from app.workers.vector_sync import process_batch


def test_durable_vector_delete(db_session: Session):
    # Setup user
    user = User(
        id="user-delete-test", email="userdel@test.com", full_name="Test User", password_hash="hash"
    )
    db_session.add(user)
    db_session.commit()

    # Create document
    doc = Document(
        id="doc-delete-test",
        user_id=user.id,
        original_name="test.pdf",
        file_type="pdf",
        file_size=100,
        content_hash="abc",
        storage_key="s3://test/abc",
        status=DocumentStatus.PROCESSED,
    )
    db_session.add(doc)

    # Create embedding profile
    profile = EmbeddingProfile(
        id="prof-123",
        document_id=doc.id,
        status="ACTIVE",
        embedding_space_id="sp-1",
        provider="gemini",
        model="gemini-1.5",
        dimension=768,
        vector_index="idx-1",
        vector_namespace="d-doc-delete-test-p-prof-123",
    )
    db_session.add(profile)

    # We need a chunk to pass `if chunk_ids:`
    from app.modules.p2_gestion_documentos_preparacion.models.document import (
        ChunkSet,
        DocumentChunk,
    )

    chunk_set = ChunkSet(
        id="cs-1",
        document_id=doc.id,
        fingerprint="fp",
        chunk_size_chars=100,
        chunk_overlap_chars=10,
    )
    db_session.add(chunk_set)
    chunk = DocumentChunk(
        id="chk-1",
        document_id=doc.id,
        chunk_set_id=chunk_set.id,
        chunk_index=0,
        content="test",
        start_char=0,
        end_char=4,
    )
    db_session.add(chunk)
    db_session.commit()

    # Mock dependencies
    storage_mock = MagicMock()
    vectors_mock = MagicMock()
    settings_mock = MagicMock()
    settings_mock.pinecone_namespace_prefix = "test"

    # Document service needs dependencies correctly
    # We need to mock get_settings inside DocumentService
    from unittest.mock import patch

    from app.modules.p2_gestion_documentos_preparacion.repositories.document_repository import (
        DocumentRepository,
    )

    with patch(
        "app.modules.p2_gestion_documentos_preparacion.services.document_service.get_settings"
    ) as mock_get_settings:
        mock_get_settings.return_value = settings_mock
        service = DocumentService(db=db_session, storage=storage_mock, vectors=vectors_mock)
        # mock things missing
        service.documents = DocumentRepository(db_session)
        service.processing = MagicMock()

        # Execute delete
        service.delete_for(user, doc.id)

    # Verify outbox records
    outbox_records = db_session.query(VectorSyncOutbox).all()
    assert len(outbox_records) == 1

    outbox = outbox_records[0]
    assert outbox.operation == "DELETE"
    assert outbox.target_namespace == "d-doc-delete-test-p-prof-123"
    assert outbox.target_index == "idx-1"
    assert outbox.status == "PENDING"
    assert outbox.chunk_id == "*"
    assert outbox.profile_id == "prof-123"

    # Now verify the worker processes the DELETE
    store_mock = MagicMock()

    # Run process_batch
    process_batch(db_session, store_mock, outbox_records)

    # Verify Pinecone call
    store_mock.delete_namespace.assert_called_once_with(
        namespace="d-doc-delete-test-p-prof-123", index_name="idx-1"
    )

    assert outbox.status == "COMPLETED"
