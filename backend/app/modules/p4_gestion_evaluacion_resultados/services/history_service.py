from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.p2_gestion_documentos_preparacion.models.document import Document
from app.modules.p3_gestion_simulacion.models.simulation import Simulation
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import (
    Evaluation,
    EvaluationStatus,
)
from app.modules.p4_gestion_evaluacion_resultados.schemas.history import (
    PerformanceHistoryItem,
    PerformanceHistoryResponse,
    PerformanceHistorySummary,
)


class HistoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_history_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        document_id: str | None = None,
        status: str | None = None
    ) -> PerformanceHistoryResponse:
        
        # 1. Base query for all user simulations to compute global summary and deltas
        base_query = (
            self.db.query(Simulation, Evaluation, Document.original_name)
            .outerjoin(Evaluation, Simulation.id == Evaluation.simulation_id)
            .join(Document, Simulation.document_id == Document.id)
            .filter(Simulation.user_id == user_id)
            .order_by(Simulation.created_at.asc())
        )
        
        all_simulations = base_query.all()
        
        # Calculate summary
        total_simulations = len(all_simulations)
        
        completed_evaluations = [
            (sim, ev, doc_title) for sim, ev, doc_title in all_simulations
            if ev and ev.status == EvaluationStatus.COMPLETED and ev.overall_score is not None
        ]
        
        evaluated_simulations = len(completed_evaluations)
        
        latest_score = completed_evaluations[-1][1].overall_score if completed_evaluations else None
        best_score = max((ev.overall_score for _, ev, _ in completed_evaluations), default=None)
        
        # Calculate deltas for each evaluated simulation chronologically
        deltas = {}
        previous_score = None
        for sim, ev, _ in completed_evaluations:
            if previous_score is not None:
                deltas[sim.id] = ev.overall_score - previous_score
            else:
                deltas[sim.id] = None
            previous_score = ev.overall_score

        # 2. Apply filters
        filtered_simulations = all_simulations
        if start_date:
            filtered_simulations = [row for row in filtered_simulations if row[0].created_at >= start_date]
        if end_date:
            filtered_simulations = [row for row in filtered_simulations if row[0].created_at <= end_date]
        if document_id:
            filtered_simulations = [row for row in filtered_simulations if row[0].document_id == document_id]
        if status:
            filtered_simulations = [
                row for row in filtered_simulations 
                if row[0].status == status or (row[1] and row[1].status == status)
            ]
            
        # 3. Sort descending for output
        filtered_simulations.sort(key=lambda x: x[0].created_at, reverse=True)
        
        # 4. Pagination
        total_items = len(filtered_simulations)
        total_pages = (total_items + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = filtered_simulations[start_idx:end_idx]
        
        # 5. Build items
        items = []
        for sim, ev, doc_title in page_items:
            duration_minutes = float(sim.planned_duration_minutes)
            if sim.started_at and sim.finished_at:
                duration_minutes = (sim.finished_at - sim.started_at).total_seconds() / 60.0

            overall_score = None
            content_score = None
            communication_score = None
            nonverbal_score = None
            ev_status = None
            delta_score = None
            
            if ev:
                ev_status = ev.status
                if ev.status == EvaluationStatus.COMPLETED and ev.overall_score is not None:
                    overall_score = ev.overall_score
                    content_score = ev.content_score
                    communication_score = ev.communication_score
                    nonverbal_score = ev.nonverbal_score
                    delta_score = deltas.get(sim.id)
            
            items.append(PerformanceHistoryItem(
                simulation_id=sim.id,
                document_title=doc_title,
                created_at=sim.created_at,
                duration_minutes=round(duration_minutes, 2),
                simulation_status=sim.status,
                evaluation_status=ev_status,
                overall_score=overall_score,
                content_score=content_score,
                communication_score=communication_score,
                nonverbal_score=nonverbal_score,
                delta_score=delta_score,
                report_url=f"/simulations/{sim.id}/report"
            ))
            
        return PerformanceHistoryResponse(
            summary=PerformanceHistorySummary(
                total_simulations=total_simulations,
                evaluated_simulations=evaluated_simulations,
                latest_score=latest_score,
                best_score=best_score
            ),
            items=items,
            total_items=total_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
