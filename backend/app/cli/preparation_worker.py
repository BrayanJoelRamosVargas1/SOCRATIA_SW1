"""Single low-memory worker. Queued tasks survive reloads and process restarts.

An interrupted external call is never automatically replayed: its outcome may
already have consumed quota. A new explicit request is required after review.
"""
import logging
import time
from datetime import UTC,datetime
from sqlalchemy import select,text,update
from app.main import app  # registers all model metadata; does not start an API server
from app.core.database import engine,SessionLocal
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import Document,DocumentStatus
from app.modules.p2_gestion_documentos_preparacion.models.preparation_task import PreparationTask

logger=logging.getLogger(__name__)
LOCK_ID=739204171

def execute_task(db,task):
    from app.integrations.embeddings.dependencies import get_embedding_provider
    from app.integrations.storage.dependencies import get_storage_provider
    from app.integrations.vector_db.dependencies import get_vector_store_provider
    from app.integrations.retrieval.dependencies import get_retrieval_router
    from app.integrations.llm.dependencies import get_question_generation_router,get_presentation_generation_router
    from app.modules.p2_gestion_documentos_preparacion.services.document_processing_service import DocumentProcessingService
    from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import QuestionBankService
    from app.modules.p2_gestion_documentos_preparacion.services.presentation_material_service import PresentationMaterialService
    user=db.get(User,task.user_id)
    if user is None or not user.is_active:raise RuntimeError("inactive_owner")
    embeddings=get_embedding_provider();vectors=get_vector_store_provider(db)
    if task.kind=="process":
        document=db.get(Document,task.document_id)
        if document.status==DocumentStatus.PROCESSED and not task.regenerate:return
        DocumentProcessingService(db,get_storage_provider(),embeddings,vectors).process(user,task.document_id)
    elif task.kind=="questions":
        service=QuestionBankService(db=db,retrieval_router=get_retrieval_router(db,embeddings,vectors),generation_router=get_question_generation_router())
        if not task.regenerate:
            from app.modules.p2_gestion_documentos_preparacion.exceptions import QuestionBankNotFoundError
            try:service.get(user,task.document_id);return
            except QuestionBankNotFoundError:pass
        service.generate(user,task.document_id)
    else:
        PresentationMaterialService(db=db,retrieval_router=get_retrieval_router(db,embeddings,vectors),generation_router=get_presentation_generation_router()).generate(user,task.document_id,duration_minutes=task.duration_minutes,regenerate=bool(task.regenerate))

def recover_interrupted(db):
    tasks=db.scalars(select(PreparationTask).where(PreparationTask.status=="RUNNING")).all()
    for task in tasks:
        task.status="INTERRUPTED";task.error_code="worker_interrupted";task.finished_at=datetime.now(UTC)
        if task.kind=="process":
            document=db.get(Document,task.document_id)
            if document and document.status!=DocumentStatus.PROCESSED:document.status=DocumentStatus.ERROR
    db.commit()
    return len(tasks)

def run_one(db,executor=execute_task):
    task=db.scalar(select(PreparationTask).where(PreparationTask.status=="QUEUED").order_by(PreparationTask.created_at).with_for_update(skip_locked=True).limit(1))
    if task is None:db.rollback();return False
    task.status="RUNNING";task.started_at=datetime.now(UTC);task_id=task.id;db.commit()
    start=time.monotonic();state="SUCCEEDED";code=None
    try:executor(db,task)
    except Exception as exc:
        db.rollback();state="FAILED";code=getattr(exc,"code","preparation_failed")
        logger.warning("Preparation failed task=%s kind=%s error_type=%s",task_id,task.kind,type(exc).__name__)
    elapsed=int((time.monotonic()-start)*1000)
    task=db.get(PreparationTask,task_id)
    if task:
        task.status=state;task.error_code=code;task.finished_at=datetime.now(UTC);task.elapsed_ms=elapsed;db.commit()
    logger.info("Preparation finished task=%s state=%s elapsed_ms=%s",task_id,state,elapsed)
    return True

def main():
    # Session advisory lock prevents a second worker from marking live work interrupted.
    with engine.connect() as lock:
        if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"),{"key":LOCK_ID}):
            raise SystemExit("A preparation worker is already running")
        lock.commit()
        with SessionLocal() as db:recover_interrupted(db)
        try:
            while True:
                try:
                    with SessionLocal() as db:worked=run_one(db)
                    if not worked:time.sleep(2)
                except Exception:
                    logger.exception("Preparation worker database error");time.sleep(5)
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"),{"key":LOCK_ID});lock.commit()

if __name__=="__main__":main()
