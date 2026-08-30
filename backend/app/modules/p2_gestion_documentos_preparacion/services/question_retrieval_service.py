from app.modules.p2_gestion_documentos_preparacion.services.document_retrieval_service import (
    DocumentContextUnavailableError,
    DocumentRetrievalService,
)

RETRIEVAL_INTENTS = (
    "objetivos, problema de investigacion, preguntas y alcance del documento",
    "metodologia, justificacion del metodo, muestra, procedimiento y decisiones metodologicas",
    "arquitectura, diseno, implementacion, componentes y propuesta tecnica",
    "resultados, evidencia, validacion, pruebas, metricas y hallazgos",
    "limitaciones, riesgos, debilidades, supuestos, amenazas a la validez y restricciones",
    "conclusiones, contribuciones, recomendaciones y trabajo futuro",
)


QuestionContextUnavailableError = DocumentContextUnavailableError


class QuestionRetrievalService(DocumentRetrievalService):
    def retrieve(self, *, user_id: str, document_id: str):
        return super().retrieve(
            user_id=user_id,
            document_id=document_id,
            intents=RETRIEVAL_INTENTS,
        )
