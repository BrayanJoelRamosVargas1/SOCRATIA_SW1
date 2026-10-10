from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import Document
from app.modules.p3_gestion_simulacion.models.simulation import Simulation
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import Evaluation


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_metrics(self) -> dict:
        total_users = self.db.query(func.count(User.id)).scalar() or 0

        # Group by status for documents
        doc_status_counts = (
            self.db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()
        )
        documents_by_status = {
            status.value if hasattr(status, "value") else status: count
            for status, count in doc_status_counts
        }

        # Group by status for simulations
        sim_status_counts = (
            self.db.query(Simulation.status, func.count(Simulation.id))
            .group_by(Simulation.status)
            .all()
        )
        simulations_by_status = {
            status.value if hasattr(status, "value") else status: count
            for status, count in sim_status_counts
        }

        # Group by status for evaluations
        eval_status_counts = (
            self.db.query(Evaluation.status, func.count(Evaluation.id))
            .group_by(Evaluation.status)
            .all()
        )
        evaluations_by_status = {
            status.value if hasattr(status, "value") else status: count
            for status, count in eval_status_counts
        }

        # Average overall_score for COMPLETED evaluations
        average_overall_score = (
            self.db.query(func.avg(Evaluation.overall_score))
            .filter(Evaluation.status == "COMPLETED")
            .scalar()
        )

        # Format the score if it's not None
        if average_overall_score is not None:
            average_overall_score = float(average_overall_score)

        return {
            "total_users": total_users,
            "documents_by_status": documents_by_status,
            "simulations_by_status": simulations_by_status,
            "evaluations_by_status": evaluations_by_status,
            "average_overall_score": average_overall_score,
            "integration_metrics": "NOT_AVAILABLE",
        }
