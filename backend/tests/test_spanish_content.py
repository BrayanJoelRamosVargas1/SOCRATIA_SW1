from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import importlib.util
import json
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.core.spanish import foreign_prose, require_spanish
from app.integrations.llm.base import (GeneratedQuestionBank, QuestionGenerationRequest,
    DocumentContextChunk, QuestionGenerationFailed, validate_question_bank)
from app.integrations.llm.router import QuestionGenerationRouter

ENGLISH = "What is the primary problem the project aims to solve, and why is it significant for university tutoring coordination?"


def request():
    return QuestionGenerationRequest(document_name="Documento de prueba", chunks=(DocumentContextChunk(id="chunk",text="La investigación estudia tutorías.",score=1),))


def bank(english=False):
    categories=["CONCEPTUAL","METHODOLOGICAL","TECHNICAL","CRITICAL"]
    return GeneratedQuestionBank.model_validate({"questions":[{
        "question":ENGLISH if english and i==0 else f"¿Cómo se justifica la decisión metodológica número {i+1} con la evidencia de la investigación?",
        "category":categories[i//3],"difficulty":"MEDIUM","source_chunk_ids":["chunk"],
        "expected_answer_points":["Explicar los resultados obtenidos en la investigación.","Relacionar la evidencia con los objetivos propuestos."]} for i in range(12)]})


@pytest.mark.parametrize("text", [ENGLISH,"What is RAG?","Why this method?","Methodology","Buenas tardes, postulante. Primera pregunta: "+ENGLISH,
    "Describe the iterative development process used for the prototype, including the types of tests performed."])
def test_detects_foreign_question_even_after_spanish_introduction(text):
    assert foreign_prose(text)
    with pytest.raises(ValueError,match="español"): require_spanish(text)


@pytest.mark.parametrize("text", ["¿Cómo validó los resultados de su investigación?",
    "La arquitectura utiliza FastAPI, PostgreSQL y React para atender las solicitudes.",
    "Google Cloud","API REST","SQL y JSON", "Describe el método utilizado.",
    "Compare los resultados de ambos grupos."])
def test_accepts_spanish_and_does_not_misclassify_short_technical_names(text):
    require_spanish(text)


def test_english_primary_uses_spanish_fallback_before_saving():
    router=QuestionGenerationRouter(primary=SimpleNamespace(name="gemini",model="test",generate=lambda _:bank(True)),
        fallback=SimpleNamespace(name="groq",model="test",generate=lambda _:bank()),failure_threshold=3,recovery_seconds=60)
    result=router.generate(request())
    assert result.fallback_used and result.provider=="groq"
    assert "invalid_output" in result.primary_failure_reason
    assert not any(foreign_prose(q.question) for q in result.bank.questions)


def test_both_foreign_providers_fail_without_accepting_english():
    provider=lambda name:SimpleNamespace(name=name,model="test",generate=lambda _:bank(True))
    with pytest.raises(QuestionGenerationFailed):
        QuestionGenerationRouter(primary=provider("gemini"),fallback=provider("groq"),failure_threshold=3,recovery_seconds=60).generate(request())


def test_rubric_language_is_checked_as_well_as_visible_questions():
    value=bank();value.questions[0].expected_answer_points=["Describe the main limitations of the proposed research method.","Identify the evidence used to justify the selected sample."]
    with pytest.raises(ValueError,match="español"):validate_question_bank(value,request())


@pytest.mark.asyncio
async def test_real_jury_adapter_rejects_english_followups_without_network(monkeypatch):
    from app.integrations.llm.jury_groq import GroqJuryRoutingProvider
    from app.integrations.llm.jury_base import JuryRoutingProviderError
    provider=GroqJuryRoutingProvider(api_key="fixture",model="fixture",timeout_seconds=1,max_attempts=1)
    monkeypatch.setattr(provider,"_request",AsyncMock(return_value=json.dumps({"action":"FOLLOW_UP","reason_code":"needs_detail","follow_up_question":ENGLISH})))
    with pytest.raises(JuryRoutingProviderError) as error:await provider.route(SimpleNamespace())
    assert error.value.kind.value=="invalid_output"


def test_repair_migration_preserves_ids_student_answers_and_rollback(client,db_session):
    from test_simulation_sessions import ready_simulation
    from app.modules.p3_gestion_simulacion.models import Simulation,SimulationTurn
    from app.modules.p1_gestion_identidad_seguridad.models.user import User
    from app.modules.p3_gestion_simulacion.services.session_service import SessionService
    from sqlalchemy import select
    id=ready_simulation(client,"spanish-repair@example.com")
    simulation=db_session.get(Simulation,id);question=simulation.questions[0];original_id=question.question_id
    question.prompt_text=ENGLISH;question.question.question=ENGLISH;db_session.commit()
    user=db_session.get(User,simulation.user_id);service=SessionService(db_session)
    snapshot=service.start(user,id)
    original_prompt=snapshot.current_question.text
    service.accept_answer(user,id,message_id=str(uuid4()),question_id=snapshot.current_question.id,content=ENGLISH,input_mode="TEXT",route_automatically=False)
    path=Path(__file__).parents[1]/"migrations/versions/20261106_0014_spanish_demo_questions.py"
    spec=importlib.util.spec_from_file_location("repair_migration",path);migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    context=MigrationContext.configure(db_session.connection())
    try:
        with Operations.context(context):migration.upgrade()
        db_session.expire_all();simulation=db_session.get(Simulation,id)
        assert simulation.questions[0].question_id==original_id
        assert simulation.questions[0].prompt_text.endswith(migration.TRANSLATIONS[ENGLISH])
        assert simulation.questions[0].question.question==migration.TRANSLATIONS[ENGLISH]
        turns=db_session.scalars(select(SimulationTurn).where(SimulationTurn.simulation_id==id)).all()
        assert next(t.content for t in turns if t.speaker=="STUDENT")==ENGLISH
        jury=next(t.content for t in turns if t.speaker=="JURY")
        assert jury.startswith("Buenas") and ENGLISH not in jury
        assert migration.TRANSLATIONS[ENGLISH] in jury
    finally:
        with Operations.context(context):migration.downgrade()
    db_session.expire_all()
    assert db_session.get(Simulation,id).questions[0].prompt_text==original_prompt


def test_english_slide_notes_are_not_accepted():
    from app.integrations.llm.presentation import GeneratedPresentation, PresentationGenerationRequest, validate_presentation
    value=GeneratedPresentation.model_validate({"title":"Defensa de investigación", "total_duration_minutes":5,"target_word_count":650,"slides":[{
      "position":i+1,"title":f"Resultados de la investigación {i+1}","objective":"Explicar las decisiones del proyecto con la evidencia disponible.",
      "bullet_points":["Resultados obtenidos con las pruebas","Limitaciones de la evaluación realizada"],
      "speaker_notes":"Explique las decisiones tomadas durante la investigación y justifique los resultados.","estimated_seconds":75,"source_chunk_ids":["chunk"]} for i in range(4)]})
    value.slides[0].speaker_notes="Explain the main findings of the research and justify the limitations of the evaluation."
    req=PresentationGenerationRequest(document_name="Documento",duration_minutes=5,chunks=request().chunks)
    with pytest.raises(ValueError,match="español"):validate_presentation(value,req)


@pytest.mark.asyncio
async def test_feedback_guard_preserves_verbatim_student_evidence():
    from app.modules.p4_gestion_evaluacion_resultados.services.evaluator import Evaluator
    from app.modules.p4_gestion_evaluacion_resultados.schemas.evaluation import TurnEvaluationResult
    response=TurnEvaluationResult(classification="PRECISE",score=90,strengths=["La respuesta justifica las decisiones con evidencia del documento."],weaknesses=[],missing_points=[],contradictions=[],evidence=[ENGLISH])
    evaluator=object.__new__(Evaluator);evaluator.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response))))
    evaluator.model="fixture";evaluator.temperature=0
    result=await evaluator.evaluate_turn("Pregunta",ENGLISH,"Contexto")
    assert result.evidence==[ENGLISH]
    response.strengths=["The response clearly identifies the main limitations of the research."]
    with pytest.raises(ValueError,match="español"):await evaluator.evaluate_turn("Pregunta",ENGLISH,"Contexto")


def test_admin_language_audit_is_paginated_private_and_does_not_scan_student_answers(client,db_session):
    from test_simulation_sessions import ready_simulation
    from test_admin_users import create_admin_and_login
    from app.modules.p3_gestion_simulacion.models import Simulation
    assert client.get("/api/v1/admin/language-audit").status_code==401
    id=ready_simulation(client,"language-audit@example.com")
    assert client.get("/api/v1/admin/language-audit").status_code==403
    simulation=db_session.get(Simulation,id);q=simulation.questions[0].question;q.question=ENGLISH;db_session.commit()
    create_admin_and_login(client,db_session)
    response=client.get("/api/v1/admin/language-audit?group=questions&limit=100")
    assert response.status_code==200
    payload=response.json();assert payload["checked"]==12 and payload["foreign_count"]==1
    assert payload["record_ids"]==[q.id] and ENGLISH not in response.text
    first=client.get("/api/v1/admin/language-audit?group=questions&limit=1").json()
    assert first["checked"]==1 and first["next_offset"]==1
    assert client.get("/api/v1/admin/language-audit?group=questions&limit=101").status_code==422


def test_followup_insertion_preserves_unique_positions_and_appears_in_report(client,db_session):
    from test_simulation_sessions import ready_simulation
    from app.modules.p3_gestion_simulacion.models import Simulation,SimulationQuestion,SimulationTurn
    from app.modules.p1_gestion_identidad_seguridad.models.user import User
    from app.modules.p3_gestion_simulacion.services.session_service import SessionService
    from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import Evaluation,TurnEvaluation
    from app.modules.p4_gestion_evaluacion_resultados.services.report_projection_service import ReportProjectionService
    from sqlalchemy import select
    id=ready_simulation(client,"followup-report@example.com");simulation=db_session.get(Simulation,id)
    user=db_session.get(User,simulation.user_id);service=SessionService(db_session);snapshot=service.start(user,id)
    service.accept_answer(user,id,message_id=str(uuid4()),question_id=snapshot.current_question.id,content="La evidencia respalda los resultados de la investigación.",route_automatically=False)
    text="¿Cómo justifica las limitaciones de la muestra seleccionada?"
    _,next_snapshot=service.add_follow_up_question(user,id,text,snapshot.current_question.id)
    assert next_snapshot.total_questions==13
    positions=db_session.scalars(select(SimulationQuestion.position).where(SimulationQuestion.simulation_id==id).order_by(SimulationQuestion.position)).all()
    assert positions==list(range(13))
    service.accept_answer(user,id,message_id=str(uuid4()),question_id=next_snapshot.current_question.id,content="La muestra solo permite conclusiones sobre las pruebas realizadas.",route_automatically=False)
    service.close_simulation(user,id)
    evaluation=Evaluation(simulation_id=id,status="COMPLETED",overall_score=80,content_score=80)
    db_session.add(evaluation);db_session.flush()
    answers=db_session.scalars(select(SimulationTurn).where(SimulationTurn.simulation_id==id,SimulationTurn.speaker=="STUDENT")).all()
    for answer in answers:db_session.add(TurnEvaluation(evaluation_id=evaluation.id,simulation_turn_id=answer.id,classification="PRECISE",turn_score=80))
    db_session.commit();db_session.expire_all()
    report=ReportProjectionService.get_simulation_report(db_session,id,user.id)
    assert len(report.questions)==2 and report.questions[1].question==text


def test_followup_cannot_link_parent_from_another_simulation(client,db_session):
    from test_simulation_sessions import ready_simulation
    from app.modules.p3_gestion_simulacion.models import Simulation
    from app.modules.p1_gestion_identidad_seguridad.models.user import User
    from app.modules.p3_gestion_simulacion.services.session_service import SessionService
    from app.modules.p3_gestion_simulacion.exceptions import InvalidTurnError
    id=ready_simulation(client,"followup-owner@example.com");simulation=db_session.get(Simulation,id)
    user=db_session.get(User,simulation.user_id);service=SessionService(db_session);snapshot=service.start(user,id)
    service.accept_answer(user,id,message_id=str(uuid4()),question_id=snapshot.current_question.id,content="Respuesta del propietario del documento.",route_automatically=False)
    other=ready_simulation(client,"followup-other@example.com");foreign=db_session.get(Simulation,other).questions[0]
    with pytest.raises(InvalidTurnError):service.add_follow_up_question(user,id,"¿Cómo valida los resultados de la investigación?",foreign.id)
    assert len(db_session.get(Simulation,id).questions)==12


def test_validation_field_messages_are_spanish(client):
    response=client.post("/api/v1/auth/register",json={"email":"bad","password":"x"})
    assert response.status_code==422
    fields=response.json()["error"]["fields"]
    assert fields and all("required" not in item["message"].lower() for item in fields)
    assert any(item["message"]=="Este campo es obligatorio." for item in fields)
