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
api_router.include_router(users_router, prefix="/profile", tags=["profile"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(questions_router, prefix="/documents", tags=["question-banks"])
api_router.include_router(presentations_router, prefix="/documents", tags=["presentations"])
api_router.include_router(admin_jury_router, prefix="/admin", tags=["admin-jury-profiles"])
api_router.include_router(simulations_router, tags=["simulations"])
api_router.include_router(simulation_websocket_router, tags=["simulation-session"])

from app.modules.p4_gestion_evaluacion_resultados.routes.evaluation_routes import (
    router as evaluation_router,
)
from app.modules.p4_gestion_evaluacion_resultados.routes.history_routes import (
    router as history_router,
)
from app.modules.p6_gestion_administracion.routes.dashboard_routes import (
    router as dashboard_router,
)

api_router.include_router(evaluation_router, tags=["evaluations"])
api_router.include_router(history_router, tags=["history"])
api_router.include_router(dashboard_router, prefix="/admin", tags=["admin-dashboard"])

from app.modules.p5_gestion_saas.routes.admin_plans import (
    router as admin_plans_router,
)
from app.modules.p5_gestion_saas.routes.admin_subscriptions import (
    router as admin_subscriptions_router,
)
from app.modules.p6_gestion_administracion.routes.admin_ai_settings_routes import (
    router as admin_ai_settings_router,
)
from app.modules.p6_gestion_administracion.routes.admin_users_routes import (
    router as admin_users_router,
)

api_router.include_router(admin_users_router, prefix="/admin", tags=["admin-users"])
api_router.include_router(
    admin_ai_settings_router, prefix="/admin", tags=["admin-ai-settings"]
)
api_router.include_router(admin_plans_router, prefix="/admin/plans", tags=["admin-plans"])
api_router.include_router(
    admin_subscriptions_router, prefix="/admin/subscriptions", tags=["admin-subscriptions"]
)

from app.modules.p5_gestion_saas.routes.student_plans import (
    router as student_plans_router,
)
from app.modules.p5_gestion_saas.routes.student_subscriptions import (
    router as student_subscriptions_router,
)

api_router.include_router(student_plans_router, prefix="/plans", tags=["student-plans"])
api_router.include_router(
    student_subscriptions_router, prefix="/subscription", tags=["student-subscriptions"]
)

from app.modules.p2_gestion_documentos_preparacion.routes.task_routes import router as preparation_tasks_router
api_router.include_router(preparation_tasks_router, prefix="/documents", tags=["preparation-tasks"])
