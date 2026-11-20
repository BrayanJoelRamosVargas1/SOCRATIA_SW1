import pytest

from app.integrations.llm.base import DocumentContextChunk
from app.integrations.llm.presentation import (
    GeneratedPresentation,
    PresentationGenerationRequest,
    parse_generated_presentation,
)


@pytest.mark.parametrize("weights", [[90] * 8, [600] + [20] * 7, [600] * 8, [20] * 8])
def test_rehearsal_schedule_fits_duration_without_changing_content(weights):
    request = PresentationGenerationRequest(
        "Investigación", 15, (DocumentContextChunk("source", "Texto", 1),)
    )
    generated = GeneratedPresentation.model_validate(
        {
            "title": "Defensa de la investigación",
            "total_duration_minutes": 15,
            "target_word_count": 1950,
            "slides": [
                {
                    "position": i + 1,
                    "title": f"Tema {i + 1}",
                    "objective": "Presentar la arquitectura técnica del prototipo.",
                    "bullet_points": ["Diseño de la investigación", "Evaluación del prototipo"],
                    "speaker_notes": "Esta sección explica la propuesta y los resultados observados en la investigación.",
                    "estimated_seconds": weight,
                    "source_chunk_ids": ["source"],
                }
                for i, weight in enumerate(weights)
            ],
        }
    )
    result = parse_generated_presentation(generated.model_dump_json(), request)
    assert sum(s.estimated_seconds for s in result.slides) == 900
    assert all(20 <= s.estimated_seconds <= 600 for s in result.slides)
    for old, new in zip(generated.slides, result.slides):
        assert old.model_dump(exclude={"estimated_seconds"}) == new.model_dump(
            exclude={"estimated_seconds"}
        )
    generated.slides[0].source_chunk_ids = ["foreign-source"]
    with pytest.raises(ValueError, match="outside"):
        parse_generated_presentation(generated.model_dump_json(), request)
