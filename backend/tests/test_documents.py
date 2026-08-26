from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from app.integrations.storage.local import LocalStorageProvider

PDF_CONTENT = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF"


def valid_docx() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<document><body /></document>")
    return buffer.getvalue()


def register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Document Student",
            "password": "secure-document-password",
        },
    )
    assert response.status_code == 201


def upload_pdf(client: TestClient, filename: str = "tesis.pdf") -> dict:
    response = client.post(
        "/api/v1/documents",
        files={"file": (filename, PDF_CONTENT, "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def stored_files(storage: LocalStorageProvider) -> list[Path]:
    if not storage.root.exists():
        return []
    return [path for path in storage.root.rglob("*") if path.is_file()]


def test_upload_document(
    client: TestClient,
    storage_provider: LocalStorageProvider,
) -> None:
    register(client, "upload@example.com")

    document = upload_pdf(client)

    assert document["original_name"] == "tesis.pdf"
    assert document["file_type"] == "PDF"
    assert document["file_size"] == len(PDF_CONTENT)
    assert document["status"] == "UPLOADED"
    files = stored_files(storage_provider)
    assert len(files) == 1
    assert files[0].read_bytes() == PDF_CONTENT


def test_list_own_documents(client: TestClient) -> None:
    register(client, "list@example.com")
    first = upload_pdf(client, "tesis.pdf")
    second = upload_pdf(client, "articulo.pdf")

    response = client.get("/api/v1/documents")

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {first["id"], second["id"]}


def test_upload_docx(client: TestClient) -> None:
    register(client, "docx@example.com")
    content = valid_docx()

    response = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "research.docx",
                content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["file_type"] == "DOCX"
    assert response.json()["file_size"] == len(content)


def test_cannot_read_other_user_document(client: TestClient) -> None:
    register(client, "owner@example.com")
    document = upload_pdf(client)
    register(client, "intruder@example.com")

    detail = client.get(f"/api/v1/documents/{document['id']}")
    processing = client.get(f"/api/v1/documents/{document['id']}/status")
    deletion = client.delete(f"/api/v1/documents/{document['id']}")

    assert detail.status_code == 404
    assert processing.status_code == 404
    assert deletion.status_code == 404
    assert client.get("/api/v1/documents").json() == []


def test_get_processing_status(client: TestClient) -> None:
    register(client, "status@example.com")
    document = upload_pdf(client)

    response = client.get(f"/api/v1/documents/{document['id']}/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "UPLOADED"
    assert len(payload["history"]) == 1
    assert payload["history"][0]["stage"] == "UPLOAD"
    assert payload["history"][0]["status"] == "UPLOADED"


def test_reject_invalid_file(client: TestClient) -> None:
    register(client, "invalid@example.com")

    wrong_extension = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    spoofed_pdf = client.post(
        "/api/v1/documents",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )

    assert wrong_extension.status_code == 422
    assert wrong_extension.json()["error"]["code"] == "invalid_document_file"
    assert spoofed_pdf.status_code == 422
    assert client.get("/api/v1/documents").json() == []


def test_delete_document(
    client: TestClient,
    storage_provider: LocalStorageProvider,
) -> None:
    register(client, "delete@example.com")
    document = upload_pdf(client)
    assert len(stored_files(storage_provider)) == 1

    response = client.delete(f"/api/v1/documents/{document['id']}")

    assert response.status_code == 204
    assert stored_files(storage_provider) == []
    assert client.get(f"/api/v1/documents/{document['id']}").status_code == 404
