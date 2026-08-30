from app.integrations.embeddings import EmbeddingError, EmbeddingProvider
from app.integrations.llm import QuestionContextChunk
from app.integrations.vector_db import VectorStoreProvider

RETRIEVAL_INTENTS = (
    "objetivos, problema de investigacion, preguntas y alcance del documento",
    "metodologia, justificacion del metodo, muestra, procedimiento y decisiones metodologicas",
    "arquitectura, diseno, implementacion, componentes y propuesta tecnica",
    "resultados, evidencia, validacion, pruebas, metricas y hallazgos",
    "limitaciones, riesgos, debilidades, supuestos, amenazas a la validez y restricciones",
    "conclusiones, contribuciones, recomendaciones y trabajo futuro",
)


class QuestionContextUnavailableError(Exception):
    """Raised when no safe context can be built for question generation."""


class QuestionRetrievalService:
    def __init__(
        self,
        *,
        embeddings: EmbeddingProvider,
        vectors: VectorStoreProvider,
        namespace_prefix: str,
        top_k: int,
        max_context_chars: int,
    ) -> None:
        self.embeddings = embeddings
        self.vectors = vectors
        self.namespace_prefix = namespace_prefix
        self.top_k = top_k
        self.max_context_chars = max_context_chars

    def retrieve(self, *, user_id: str, document_id: str) -> tuple[QuestionContextChunk, ...]:
        query_vectors = self.embeddings.embed_queries(list(RETRIEVAL_INTENTS))
        if len(query_vectors) != len(RETRIEVAL_INTENTS):
            raise EmbeddingError("Embedding count does not match retrieval intent count")

        namespace = f"{self.namespace_prefix}-{user_id}"
        filters = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$eq": document_id}},
            ]
        }
        deduplicated: dict[str, QuestionContextChunk] = {}
        for query_vector in query_vectors:
            matches = self.vectors.query(
                namespace=namespace,
                vector=query_vector,
                top_k=self.top_k,
                filters=filters,
            )
            for match in matches:
                metadata = match.metadata
                if metadata.get("user_id") != user_id:
                    continue
                if metadata.get("document_id") != document_id:
                    continue
                text = metadata.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                existing = deduplicated.get(match.id)
                if existing is None:
                    deduplicated[match.id] = QuestionContextChunk(
                        id=match.id,
                        text=text.strip(),
                        score=match.score,
                    )
                elif match.score > existing.score:
                    deduplicated[match.id] = QuestionContextChunk(
                        id=match.id,
                        text=existing.text,
                        score=match.score,
                    )

        packed: list[QuestionContextChunk] = []
        used_chars = 0
        for chunk in deduplicated.values():
            if packed and used_chars + len(chunk.text) > self.max_context_chars:
                continue
            packed.append(chunk)
            used_chars += len(chunk.text)
        if not packed:
            raise QuestionContextUnavailableError
        return tuple(packed)
