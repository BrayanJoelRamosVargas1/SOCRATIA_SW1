from app.integrations.llm.base import DocumentContextChunk
from app.integrations.llm.presentation import (
    PRESENTATION_JSON_SCHEMA,
    PresentationGenerationRequest,
    presentation_json_schema,
)


def test_generation_schema_enforces_duration_bullets_and_real_sources():
    request = PresentationGenerationRequest(
        document_name="Ensayo",
        duration_minutes=15,
        chunks=(DocumentContextChunk(id="actual-chunk", text="Evidencia", score=1),),
    )
    schema = presentation_json_schema(request)
    properties = schema["properties"]
    assert properties["total_duration_minutes"]["enum"] == [15]
    assert properties["target_word_count"]["enum"] == [1950]
    assert properties["slides"]["minItems"] == 8
    assert properties["slides"]["maxItems"] == 12
    slide = properties["slides"]["items"]["properties"]
    assert slide["bullet_points"]["maxItems"] == 5
    assert slide["source_chunk_ids"]["items"]["enum"] == ["actual-chunk"]
    assert "minItems" not in PRESENTATION_JSON_SCHEMA["properties"]["slides"]


def test_schema_is_scoped_per_request_without_cross_document_sources():
    first = PresentationGenerationRequest("Uno", 5, (DocumentContextChunk("one", "Texto", 1),))
    second = PresentationGenerationRequest("Dos", 30, (DocumentContextChunk("two", "Texto", 1),))
    a, b = presentation_json_schema(first), presentation_json_schema(second)
    assert a["properties"]["slides"]["items"]["properties"]["source_chunk_ids"]["items"][
        "enum"
    ] == ["one"]
    assert b["properties"]["slides"]["minItems"] == 14
    assert b["properties"]["slides"]["items"]["properties"]["source_chunk_ids"]["items"][
        "enum"
    ] == ["two"]
