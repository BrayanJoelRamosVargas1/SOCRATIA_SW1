import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.integrations.llm.jury_base import (
    JuryAction,
    JuryRoutingDecision,
    JuryRoutingFailed,
    JuryRoutingProvider,
    JuryRoutingProviderError,
    JuryRoutingRequest,
    LLMErrorKind,
)
from app.integrations.llm.jury_router import JuryRoutingRouter
from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import UserRepository
from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import (
    QuestionBankService,
)
from app.modules.p4_gestion_evaluacion_resultados.services.evaluation_service import (
    EvaluationService,
)
from app.modules.p6_gestion_administracion.services.ai_configuration_service import (
    AIConfigurationService,
)


def create_admin_and_login(client: TestClient, db_session: Session) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin_ai@test.com",
            "full_name": "Admin AI User",
            "password": "this_is_a_strong_password",
        },
    )
    repo = UserRepository(db_session)
    user = repo.get_by_email("admin_ai@test.com")
    role = repo.get_or_create_role("Administrator")
    user.roles.append(role)
    db_session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_ai@test.com", "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    client.cookies.set("socratia_access", token)
    return {"token": token, "user": user}


def create_student_and_login(client: TestClient, db_session: Session) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "student_ai@test.com",
            "full_name": "Student AI User",
            "password": "this_is_a_strong_password",
        },
    )
    repo = UserRepository(db_session)
    user = repo.get_by_email("student_ai@test.com")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "student_ai@test.com", "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    client.cookies.set("socratia_access", token)
    return {"token": token, "user": user}


# 1. GET admin success
def test_01_get_ai_settings_admin_success(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.get("/api/v1/admin/ai-settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "jury_provider" in data
    assert "jury_model" in data
    assert "retrieval_top_k" in data
    assert "config_version" in data
    assert data["config_version"] >= 1


# 2. GET student forbidden
def test_02_get_ai_settings_student_forbidden(client: TestClient, db_session: Session) -> None:
    create_student_and_login(client, db_session)
    resp = client.get("/api/v1/admin/ai-settings")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Administrator access required"


# 3. GET anonymous unauthorized
def test_03_get_ai_settings_anonymous_unauthorized(client: TestClient) -> None:
    client.cookies.clear()
    resp = client.get("/api/v1/admin/ai-settings")
    assert resp.status_code == 401


# 4. PATCH admin success
def test_04_patch_ai_settings_admin_success(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    payload = {
        "jury_temperature": 0.45,
        "retrieval_top_k": 8,
        "max_followups": 3,
    }
    resp = client.patch("/api/v1/admin/ai-settings", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["jury_temperature"] == 0.45
    assert data["retrieval_top_k"] == 8
    assert data["max_followups"] == 3


# 5. PATCH student forbidden
def test_05_patch_ai_settings_student_forbidden(client: TestClient, db_session: Session) -> None:
    create_student_and_login(client, db_session)
    resp = client.patch("/api/v1/admin/ai-settings", json={"retrieval_top_k": 5})
    assert resp.status_code == 403


# 6. PATCH anonymous unauthorized
def test_06_patch_ai_settings_anonymous_unauthorized(client: TestClient) -> None:
    client.cookies.clear()
    resp = client.patch("/api/v1/admin/ai-settings", json={"retrieval_top_k": 5})
    assert resp.status_code == 401


# 7. GET options admin success
def test_07_get_options_admin_success(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.get("/api/v1/admin/ai-settings/options")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert "limits" in data
    provider_ids = [p["id"] for p in data["providers"]]
    assert "groq" in provider_ids
    assert "gemini" in provider_ids


# 8. GET options student forbidden
def test_08_get_options_student_forbidden(client: TestClient, db_session: Session) -> None:
    create_student_and_login(client, db_session)
    resp = client.get("/api/v1/admin/ai-settings/options")
    assert resp.status_code == 403


# 9. GET options anonymous unauthorized
def test_09_get_options_anonymous_unauthorized(client: TestClient) -> None:
    client.cookies.clear()
    resp = client.get("/api/v1/admin/ai-settings/options")
    assert resp.status_code == 401


# 10. GET never exposes API keys
def test_10_get_never_exposes_api_keys(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.get("/api/v1/admin/ai-settings")
    assert resp.status_code == 200
    data = resp.json()
    for key in data.keys():
        assert "key" not in key.lower()
        assert "secret" not in key.lower()
        assert "token" not in key.lower() or key == "jury_max_tokens"


# 11. GET options never exposes API keys
def test_11_get_options_never_exposes_api_keys(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.get("/api/v1/admin/ai-settings/options")
    assert resp.status_code == 200
    raw_text = resp.text
    assert "sk-" not in raw_text
    assert "api_key" not in raw_text
    data = resp.json()
    for p in data["providers"]:
        assert isinstance(p["is_configured"], bool)
        assert "key" not in p


# 12. PATCH rejects extra fields (extra="forbid")
def test_12_patch_rejects_extra_fields(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"retrieval_top_k": 5, "unknown_field": "disallowed"},
    )
    assert resp.status_code == 422


# 13. PATCH rejects api_key injection
def test_13_patch_rejects_api_key_field(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"api_key": "some_injected_key"},
    )
    assert resp.status_code == 422


# 14. PATCH rejects gemini_api_key injection
def test_14_patch_rejects_gemini_api_key_field(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"gemini_api_key": "secret_key_123"},
    )
    assert resp.status_code == 422


# 15. PATCH rejects invalid jury provider
def test_15_patch_rejects_invalid_jury_provider(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"jury_provider": "claude"},
    )
    assert resp.status_code == 422


# 16. PATCH rejects invalid evaluation provider
def test_16_patch_rejects_invalid_evaluation_provider(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"evaluation_provider": "anthropic"},
    )
    assert resp.status_code == 422


# 17. PATCH rejects top_k = 0
def test_17_patch_rejects_top_k_zero(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"retrieval_top_k": 0},
    )
    assert resp.status_code == 422


# 18. PATCH rejects top_k negative
def test_18_patch_rejects_top_k_negative(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"retrieval_top_k": -4},
    )
    assert resp.status_code == 422


# 19. PATCH rejects top_k above 20
def test_19_patch_rejects_top_k_above_twenty(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"retrieval_top_k": 21},
    )
    assert resp.status_code == 422


# 20. PATCH rejects negative jury temperature
def test_20_patch_rejects_negative_jury_temperature(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"jury_temperature": -0.05},
    )
    assert resp.status_code == 422


# 21. PATCH rejects excessive jury temperature
def test_21_patch_rejects_excessive_jury_temperature(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"jury_temperature": 1.05},
    )
    assert resp.status_code == 422


# 22. PATCH rejects negative evaluation temperature
def test_22_patch_rejects_negative_evaluation_temperature(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"evaluation_temperature": -0.1},
    )
    assert resp.status_code == 422


# 23. PATCH rejects excessive evaluation temperature
def test_23_patch_rejects_excessive_evaluation_temperature(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"evaluation_temperature": 1.2},
    )
    assert resp.status_code == 422


# 24. PATCH rejects low jury_max_tokens (<256)
def test_24_patch_rejects_low_jury_max_tokens(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"jury_max_tokens": 128},
    )
    assert resp.status_code == 422


# 25. PATCH rejects high jury_max_tokens (>4096)
def test_25_patch_rejects_high_jury_max_tokens(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"jury_max_tokens": 8192},
    )
    assert resp.status_code == 422


# 26. PATCH rejects negative max_followups
def test_26_patch_rejects_negative_max_followups(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"max_followups": -1},
    )
    assert resp.status_code == 422


# 27. PATCH rejects excessive max_followups (>5)
def test_27_patch_rejects_excessive_max_followups(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"max_followups": 6},
    )
    assert resp.status_code == 422


# 28. PATCH rejects incompatible model for provider
def test_28_patch_rejects_incompatible_model_for_provider(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)
    resp = client.patch(
        "/api/v1/admin/ai-settings",
        json={"jury_provider": "groq", "jury_model": "gemini-1.5-flash"},
    )
    assert resp.status_code == 422


# 29. Monotonic config_version increment
def test_29_config_version_increments_monotonically(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)
    r1 = client.patch("/api/v1/admin/ai-settings", json={"retrieval_top_k": 5})
    v1 = r1.json()["config_version"]

    r2 = client.patch("/api/v1/admin/ai-settings", json={"retrieval_top_k": 6})
    v2 = r2.json()["config_version"]

    r3 = client.patch("/api/v1/admin/ai-settings", json={"retrieval_top_k": 7})
    v3 = r3.json()["config_version"]

    assert v2 == v1 + 1
    assert v3 == v2 + 1


# 30. updated_by tracks acting admin id
def test_30_updated_by_tracks_admin_id(client: TestClient, db_session: Session) -> None:
    auth = create_admin_and_login(client, db_session)
    admin_id = auth["user"].id

    resp = client.patch("/api/v1/admin/ai-settings", json={"retrieval_top_k": 9})
    assert resp.status_code == 200
    assert resp.json()["updated_by"] == admin_id


# 31. Immediate runtime retrieval_top_k consumption in QuestionBankService
def test_31_runtime_retrieval_top_k_immediate_consumption(
    client: TestClient,
    db_session: Session,
    question_router,
) -> None:
    from unittest.mock import MagicMock

    create_admin_and_login(client, db_session)

    mock_router = MagicMock()
    # Initial retrieval top_k is 4
    service = QuestionBankService(
        db=db_session,
        retrieval_router=mock_router,
        generation_router=question_router,
    )
    assert service.retrieval.top_k == 4

    # Patch top_k to 12
    client.patch("/api/v1/admin/ai-settings", json={"retrieval_top_k": 12})

    # A subsequent service or call immediately reflects 12 without restarting
    service_after = QuestionBankService(
        db=db_session,
        retrieval_router=mock_router,
        generation_router=question_router,
    )
    assert service_after.retrieval.top_k == 12


# 32. Immediate runtime jury configuration consumption
def test_32_runtime_jury_parameters_immediate_consumption(
    client: TestClient, db_session: Session
) -> None:
    from app.integrations.llm.dependencies import get_jury_routing_router

    create_admin_and_login(client, db_session)

    # Patch jury to gemini with temperature 0.75 and max_tokens 1024
    patch_payload = {
        "jury_provider": "gemini",
        "jury_model": "gemini-1.5-flash",
        "jury_temperature": 0.75,
        "jury_max_tokens": 1024,
    }
    resp = client.patch("/api/v1/admin/ai-settings", json=patch_payload)
    assert resp.status_code == 200

    # Get router with db context
    router = get_jury_routing_router(db=db_session)
    assert router.primary.name == "gemini"
    assert router.primary.model == "gemini-1.5-flash"
    assert router.primary.temperature == 0.75
    assert router.primary.max_tokens == 1024
    assert router.fallback.name == "groq"


# 33. Immediate runtime evaluator configuration consumption
def test_33_runtime_evaluator_parameters_immediate_consumption(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)

    # Patch evaluation parameters
    patch_payload = {
        "evaluation_provider": "gemini",
        "evaluation_model": "gemini-2.0-flash",
        "evaluation_temperature": 0.35,
    }
    resp = client.patch("/api/v1/admin/ai-settings", json=patch_payload)
    assert resp.status_code == 200

    # EvaluationService instantiated with db immediately picks up gemini & temperature 0.35
    eval_service = EvaluationService(db=db_session)
    assert eval_service.evaluator.provider == "gemini"
    assert eval_service.evaluator.model == "gemini-2.0-flash"
    assert eval_service.evaluator.temperature == 0.35


# 34. Runtime max_followups enforcement
def test_34_runtime_max_followups_immediate_consumption(
    client: TestClient, db_session: Session
) -> None:
    create_admin_and_login(client, db_session)

    # Update max_followups to 1
    resp = client.patch("/api/v1/admin/ai-settings", json={"max_followups": 1})
    assert resp.status_code == 200

    config = AIConfigurationService(db_session).get_active_config()
    assert config.max_followups == 1


# 35. Fallback enabled vs disabled behavior
@pytest.mark.asyncio
async def test_35_fallback_resilience_and_toggle() -> None:
    class FailingProvider(JuryRoutingProvider):
        name = "mock_primary"
        model = "failing-model"

        async def route(self, request: JuryRoutingRequest) -> JuryRoutingDecision:
            raise JuryRoutingProviderError(
                "Primary is down",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
            )

    class WorkingFallback(JuryRoutingProvider):
        name = "mock_fallback"
        model = "working-model"

        async def route(self, request: JuryRoutingRequest) -> JuryRoutingDecision:
            return JuryRoutingDecision(
                action=JuryAction.NEXT_BANK,
                reason_code="ok_fallback",
            )

    req = JuryRoutingRequest(
        question_text="Pregunta",
        expected_answer_points=["Punto"],
        student_answer="Respuesta",
        focus_type="METHODOLOGICAL",
        strictness=3,
        interruption_level="MEDIUM",
    )

    # When fallback_enabled is True: fallback is called and succeeds
    resilient_router = JuryRoutingRouter(
        primary=FailingProvider(),
        fallback=WorkingFallback(),
        failure_threshold=3,
        recovery_seconds=60,
        fallback_enabled=True,
    )
    result = await resilient_router.route(req)
    assert result.fallback_used is True
    assert result.provider == "mock_fallback"

    # When fallback_enabled is False: error is raised without attempting fallback
    strict_router = JuryRoutingRouter(
        primary=FailingProvider(),
        fallback=WorkingFallback(),
        failure_threshold=3,
        recovery_seconds=60,
        fallback_enabled=False,
    )
    with pytest.raises(JuryRoutingFailed) as exc_info:
        await strict_router.route(req)
    assert "fallback is disabled" in str(exc_info.value)
