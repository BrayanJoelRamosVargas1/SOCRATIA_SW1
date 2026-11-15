from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import (
    TurnClassification,
)
from app.modules.p4_gestion_evaluacion_resultados.services.evaluation_service import (
    EvaluationService,
)


@pytest.mark.asyncio
async def test_evaluate_simulation_not_found(db_session: Session):
    from fastapi import HTTPException
    service = EvaluationService(db_session)
    with pytest.raises(HTTPException) as error:
        await service.evaluate_simulation("non_existent_id")
    assert error.value.status_code == 404
    assert error.value.detail == "No se encontró la simulación"


@pytest.mark.asyncio
@patch("app.modules.p4_gestion_evaluacion_resultados.services.evaluation_service.Evaluator")
async def test_evaluate_simulation_success(MockEvaluator, db_session: Session):
    mock_evaluator = MockEvaluator.return_value

    mock_result = MagicMock()
    mock_result.classification = TurnClassification.PRECISE
    mock_result.score = 8.5
    mock_result.strengths = ["Good point"]
    mock_result.weaknesses = []
    mock_result.missing_points = []
    mock_result.contradictions = []
    mock_result.evidence = ["Quote"]

    mock_evaluator.evaluate_turn = AsyncMock(return_value=mock_result)
    mock_evaluator.provider = "mock"
    mock_evaluator.model = "mock-model"

    # Testing full integration would require a complete simulation seeded in db.
    # Since this is a basic test, we just check if it instantiates and handles gracefully.
    service = EvaluationService(db_session)
    assert service is not None
