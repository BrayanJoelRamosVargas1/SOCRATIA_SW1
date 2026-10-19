from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.exceptions import DomainError
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p2_gestion_documentos_preparacion.models.document import Document, DocumentStatus
from app.modules.p2_gestion_documentos_preparacion.models.preparation_task import PreparationTask
from app.modules.p2_gestion_documentos_preparacion.policies.document_policy import DocumentPolicy

router=APIRouter()
Database=Annotated[Session,Depends(get_db)]
class TaskInput(BaseModel):
    kind: Literal["process","questions","presentation"]
    request_key: UUID
    duration_minutes: int=Field(default=15,ge=5,le=30)
    regenerate: bool=False
class TaskResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:str
    document_id:str
    kind:str
    status:str
    duration_minutes:int
    error_code:str|None
    created_at:datetime
    started_at:datetime|None
    finished_at:datetime|None
    elapsed_ms:int|None

@router.get("/{document_id}/tasks",response_model=list[TaskResponse])
def list_tasks(document_id:str,current_user:CurrentUser,db:Database):
    DocumentPolicy.can_read(current_user,db.get(Document,document_id))
    return db.scalars(select(PreparationTask).where(PreparationTask.document_id==document_id,
        PreparationTask.user_id==current_user.id).order_by(PreparationTask.created_at.desc()).limit(10)).all()

@router.post("/{document_id}/tasks",response_model=TaskResponse,status_code=202)
def enqueue_task(document_id:str,body:TaskInput,current_user:CurrentUser,db:Database):
    # Serialize submissions for this document, including concurrent requests in different tabs.
    document=DocumentPolicy.can_read(current_user,db.scalar(select(Document).where(Document.id==document_id).with_for_update()))
    prior=db.scalar(select(PreparationTask).where(PreparationTask.user_id==current_user.id,
        PreparationTask.request_key==str(body.request_key)))
    if prior:
        if prior.document_id!=document_id or prior.kind!=body.kind or prior.duration_minutes!=body.duration_minutes or bool(prior.regenerate)!=body.regenerate:
            raise DomainError("La solicitud ya existe con otros datos.",code="task_key_conflict",status_code=409)
        return prior
    active=db.scalar(select(PreparationTask).where(PreparationTask.document_id==document_id,
        PreparationTask.status.in_(["QUEUED","RUNNING"])))
    if active:
        if active.kind==body.kind and active.duration_minutes==body.duration_minutes and bool(active.regenerate)==body.regenerate:
            return active
        raise DomainError("Ya hay una preparación en curso para este documento.",code="task_in_progress",status_code=409)
    if body.kind!="process" and document.status!=DocumentStatus.PROCESSED:
        raise DomainError("Procesa primero el documento.",code="document_not_processed",status_code=409)
    if body.kind=="process" and document.status not in (DocumentStatus.UPLOADED,DocumentStatus.ERROR,DocumentStatus.PROCESSED):
        raise DomainError("El documento ya se está procesando.",code="task_in_progress",status_code=409)
    task=PreparationTask(user_id=current_user.id,document_id=document_id,kind=body.kind,
        request_key=str(body.request_key),duration_minutes=body.duration_minutes,regenerate=int(body.regenerate))
    db.add(task);db.commit();db.refresh(task)
    return task
