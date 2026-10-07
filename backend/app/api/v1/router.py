from fastapi import APIRouter

from app.modules.p1_gestion_identidad_seguridad.routes.auth_routes import (
    router as auth_router,
)
from app.modules.p1_gestion_identidad_seguridad.routes.user_routes import (
    router as users_router,
)
from app.modules.p2_gestion_documentos_preparacion.routes.document_routes import (
    router as documents_router,
)
from app.modules.p2_gestion_documentos_preparacion.routes.presentation_routes import (
    router as presentations_router,
)
from app.modules.p2_gestion_documentos_preparacion.routes.question_routes import (
    router as questions_router,
)
from app.modules.p3_gestion_simulacion.routes.admin_jury_routes import (
    router as admin_jury_router,
)
from app.modules.p3_gestion_simulacion.routes.session_websocket import (
    router as simulation_websocket_router,
)
from app.modules.p3_gestion_simulacion.routes.simulation_routes import (
    router as simulations_router,
)

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(questions_router, prefix="/documents", tags=["question-banks"])
api_router.include_router(presentations_router, prefix="/documents", tags=["presentations"])
api_router.include_router(admin_jury_router, prefix="/admin", tags=["admin-jury-profiles"])
api_router.include_router(simulations_router, tags=["simulations"])
api_router.include_router(simulation_websocket_router, tags=["simulation-session"])

from app.modules.p4_gestion_evaluacion_resultados.routes.evaluation_routes import (
    router as evaluation_router,
)

api_router.include_router(evaluation_router, tags=["evaluations"])
