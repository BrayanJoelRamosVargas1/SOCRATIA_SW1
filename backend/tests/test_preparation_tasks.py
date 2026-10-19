from uuid import uuid4
from sqlalchemy import select
from app.modules.p2_gestion_documentos_preparacion.models.preparation_task import PreparationTask
from app.cli.preparation_worker import run_one,recover_interrupted
from test_presentation_materials import register,upload,processed

def request(kind="process",**extra):return {"kind":kind,"request_key":str(uuid4()),**extra}

def test_queue_is_owner_scoped_and_deduplicates(client,db_session):
    register(client,"queue@example.com");doc=upload(client);url=f"/api/v1/documents/{doc}/tasks"
    body=request();first=client.post(url,json=body)
    assert first.status_code==202
    assert first.json()["status"]=="QUEUED"
    assert client.post(url,json=body).json()["id"]==first.json()["id"]
    assert client.post(url,json=request()).json()["id"]==first.json()["id"]
    assert len(client.get(url).json())==1
    register(client,"outsider@example.com")
    assert client.get(url).status_code==404
    assert client.post(url,json=request()).status_code==404

def test_completed_key_does_not_repeat_external_work(client,db_session):
    register(client,"done@example.com");doc=upload(client);url=f"/api/v1/documents/{doc}/tasks";body=request()
    task_id=client.post(url,json=body).json()["id"];calls=[]
    assert run_one(db_session,lambda db,task:calls.append(task.id))
    assert not run_one(db_session,lambda db,task:calls.append(task.id))
    assert calls==[task_id]
    done=client.post(url,json=body).json()
    assert done["status"]=="SUCCEEDED" and done["elapsed_ms"]>=0
    assert done["id"]==task_id

def test_failed_worker_does_not_replay_or_expose_exception(client,db_session):
    register(client,"failure@example.com");doc=upload(client);url=f"/api/v1/documents/{doc}/tasks"
    client.post(url,json=request())
    def fail(db,task):raise RuntimeError("PRIVATE PROVIDER KEY AND PROMPT")
    run_one(db_session,fail)
    rows=client.get(url).json()
    assert rows[0]["status"]=="FAILED"
    assert rows[0]["error_code"]=="preparation_failed"
    assert "PRIVATE" not in str(rows)
    assert not run_one(db_session,fail)

def test_restart_marks_only_inflight_interrupted(client,db_session):
    register(client,"restart@example.com");doc=upload(client);url=f"/api/v1/documents/{doc}/tasks"
    task_id=client.post(url,json=request()).json()["id"]
    task=db_session.get(PreparationTask,task_id);task.status="RUNNING";db_session.commit()
    assert recover_interrupted(db_session)==1
    assert client.get(url).json()[0]["status"]=="INTERRUPTED"
    assert not run_one(db_session,lambda *_:None)

def test_conflicting_key_and_parallel_kinds_rejected(client,db_session):
    doc=processed(client,"conflict@example.com");url=f"/api/v1/documents/{doc}/tasks"
    body=request("presentation",duration_minutes=10)
    assert client.post(url,json=body).status_code==202
    assert client.post(url,json={**body,"duration_minutes":20}).status_code==409
    assert client.post(url,json=request("questions")).status_code==409
    assert client.post(url,json=request("presentation",duration_minutes=60)).status_code==422

def test_preparation_requires_processed_document(client):
    register(client,"unprocessed@example.com");doc=upload(client)
    assert client.post(f"/api/v1/documents/{doc}/tasks",json=request("presentation")).status_code==409


def test_worker_executes_all_preparation_kinds_with_isolated_providers(client,db_session,monkeypatch,embedding_provider,vector_store,storage_provider,question_router,presentation_router):
    import app.integrations.embeddings.dependencies as embedding_deps
    import app.integrations.vector_db.dependencies as vector_deps
    import app.integrations.storage.dependencies as storage_deps
    import app.integrations.llm.dependencies as llm_deps
    from app.cli.preparation_worker import execute_task
    monkeypatch.setattr(embedding_deps,"get_embedding_provider",lambda:embedding_provider)
    monkeypatch.setattr(vector_deps,"get_vector_store_provider",lambda db:vector_store)
    monkeypatch.setattr(storage_deps,"get_storage_provider",lambda:storage_provider)
    monkeypatch.setattr(llm_deps,"get_question_generation_router",lambda:question_router)
    monkeypatch.setattr(llm_deps,"get_presentation_generation_router",lambda:presentation_router)
    register(client,"fullworker@example.com");doc=upload(client);url=f"/api/v1/documents/{doc}/tasks"
    for kind in ("process","questions","presentation"):
        queued=client.post(url,json=request(kind))
        assert queued.status_code==202
        assert run_one(db_session,execute_task)
        assert client.get(url).json()[0]["status"]=="SUCCEEDED"
    assert client.get(f"/api/v1/documents/{doc}").json()["status"]=="PROCESSED"
    assert client.get(f"/api/v1/documents/{doc}/questions").status_code==200
    assert client.get(f"/api/v1/documents/{doc}/presentation").status_code==200
    assert client.get("/health").headers["server-timing"].startswith("app;dur=")
