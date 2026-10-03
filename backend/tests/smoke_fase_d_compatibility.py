import logging
import math
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingDocument
from app.integrations.embeddings.huggingface_e5 import HuggingFaceE5Provider
from app.integrations.embeddings.local_e5 import LocalE5Provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fase_d_compatibility")


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = math.sqrt(sum(x * x for x in v1))
    norm_v2 = math.sqrt(sum(y * y for y in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


def l2_norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def get_top_k(query_vec, passages_vecs, k=5):
    scores = [(i, cosine_similarity(query_vec, p_vec)) for i, p_vec in enumerate(passages_vecs)]
    scores.sort(key=lambda x: x[1], reverse=True)
    return [i for i, _ in scores[:k]]


def compute_agreement(remote_top, local_top, k):
    r_k = remote_top[:k]
    l_k = local_top[:k]
    overlap = len(set(r_k) & set(l_k))
    return (overlap / k) * 100.0 if k > 0 else 0.0


def run_golden_test():
    settings = get_settings()
    api_key = (
        settings.huggingface_api_key.get_secret_value() if settings.huggingface_api_key else None
    )

    if not api_key:
        logger.warning("SKIP: HUGGINGFACE_API_KEY is not configured.")
        return

    logger.info("Initializing Hugging Face Remote E5...")
    hf_remote = HuggingFaceE5Provider(
        api_key=api_key,
        model=settings.e5_embedding_model,
        dimensions=768,
    )

    logger.info("Initializing Local E5...")
    # Force use of local implementation with the expected revision
    hf_local = LocalE5Provider(
        model_name=settings.e5_embedding_model,
        dimensions=768,
    )

    if not hf_local.is_available:
        logger.error("Local E5 is not available. Please install dependencies.")
        return

    logger.info(
        "HF Remote Space: %s | Local E5 Space: %s",
        hf_remote.embedding_space_id,
        hf_local.embedding_space_id,
    )
    if hf_remote.embedding_space_id == hf_local.embedding_space_id:
        logger.warning(
            "WARNING: Spaces are identical! This test is meant to evaluate them before unification."
        )

    queries = [
        "¿Por qué utilizaron PostgreSQL?",
        "¿Qué arquitectura utiliza el sistema?",
        "¿Cómo funciona el módulo RAG?",
        "¿Cuáles son las limitaciones?",
        "¿Qué base de datos de vectores se utiliza?",
    ]

    # 30 simulated real-world chunks from a technical document
    passages = [
        "Para el almacenamiento relacional, se seleccionó PostgreSQL debido a su robustez y soporte para transacciones ACID. Esto garantiza la integridad de los datos de usuarios y documentos.",
        "El sistema implementa una Arquitectura Hexagonal (Puertos y Adaptadores). Esta decisión permite aislar el dominio de la infraestructura, facilitando el cambio de proveedores en el futuro.",
        "La base de datos PostgreSQL almacena los metadatos de los documentos y perfiles de usuarios. No se utiliza para búsqueda vectorial, rol que cumple Pinecone.",
        "El módulo RAG (Retrieval-Augmented Generation) opera tomando la consulta del usuario, convirtiéndola en un vector, y buscando los chunks más similares en Pinecone.",
        "Una de las limitaciones identificadas es la cuota de la capa gratuita de los modelos comerciales, lo que motivó la inclusión de E5 local como mecanismo de fallback.",
        "El sistema está desarrollado en Python 3.12 usando FastAPI por su soporte asíncrono y excelente rendimiento en operaciones I/O limitadas.",
        "Se seleccionó Pinecone como base de datos vectorial principal (Vector Store) porque ofrece una latencia mínima y gestión de índices cloud-native.",
        "Los embeddings se generan usando Gemini, Cohere, o Hugging Face (Multilingual E5). Todos generan vectores que se insertan en namespaces separados.",
        "Para generar embeddings localmente sin depender de internet, se implementó SentenceTransformers corriendo con local_files_only=True.",
        "Cada documento es dividido en chunks de 3000 caracteres con un overlap de 400. Esto asegura que no se pierda contexto en los límites de los fragmentos.",
        "La interfaz de usuario está construida en Next.js con TailwindCSS. Se comunica con el backend a través de endpoints RESTful bajo el prefijo /api/v1.",
        "La autenticación se realiza mediante JWT (JSON Web Tokens). El token de acceso tiene un tiempo de vida corto, mientras que el refresh token permite mantener la sesión activa.",
        "El contenedor de Docker para el backend incluye todas las dependencias necesarias. Sin embargo, para la FASE D se modularizó el entorno de ML para no sobrecargar el core.",
        "Durante las pruebas de estrés, el sistema demostró poder manejar 129 chunks correspondientes a un PDF de 16.7 MB en menos de 5 minutos utilizando los modelos remotos.",
        "El componente de extracción de texto utiliza bibliotecas como pdfplumber o PyPDF2 para obtener el contenido crudo antes del chunking.",
        "Cuando el coordinador detecta que el proveedor principal (ej. Gemini) falla (HTTP 429 o 503), lanza un FallbackTriggered y cambia al siguiente proveedor en la cadena.",
        "Pinecone organiza los datos en 'namespaces'. En Socratia, cada combinación de documento y perfil de embedding recibe un namespace único para evitar colisiones.",
        "Si ocurre un EXECUTOR_CHANGE (por ejemplo, HF a Local E5, si ambos comparten el mismo espacio matemático), el sistema reanuda el procesamiento desde el último chunk insertado.",
        "Si ocurre un SPACE_CHANGE (por ejemplo, Gemini 768d a Cohere 1024d), el sistema debe crear un nuevo índice de staging y empezar desde el chunk 0.",
        "El fallback local se activa solo cuando todas las APIs externas fallan, asegurando la continuidad del negocio en ambientes sin conectividad.",
        "Se implementó un límite estricto de concurrencia para el procesamiento local del modelo E5 usando un ThreadPoolExecutor, evitando bloquear el event loop de FastAPI.",
        "El modelo multilingual-e5-base requiere que las consultas comiencen con el prefijo 'query: ' y los pasajes con 'passage: ' para funcionar correctamente.",
        "La validación de la fase D incluyó el diseño de un 'Golden Test' para asegurar que la similitud de coseno entre los vectores locales y remotos fuera superior a 0.999.",
        "El framework SQLAlchemy se usa como ORM para interactuar con la base de datos PostgreSQL, facilitando las migraciones con Alembic.",
        "El servicio de Storage utiliza AWS S3 (o un emulador local como MinIO) para almacenar los archivos PDF y DOCX subidos por los usuarios antes de procesarlos.",
        "El costo del despliegue en producción se mantiene al mínimo usando capas gratuitas y arquitecturas serverless donde es posible, excepto en el worker de ML local.",
        "En el contexto RAG, se devuelven los top-4 fragmentos más relevantes y se insertan en el prompt del LLM (Gemini-Flash o Llama3).",
        "El diseño de dominio está estructurado en módulos, por ejemplo p1_gestion_identidad y p2_gestion_documentos, siguiendo los principios de Bounded Contexts.",
        "Las variables de configuración del sistema se leen desde el entorno mediante pydantic-settings, lo que permite diferentes perfiles para dev, testing y producción.",
        "Se incluyó una política estricta de CORS en la API de FastAPI para permitir peticiones únicamente desde el dominio del frontend.",
    ]

    docs = [EmbeddingDocument(title=None, text=t) for t in passages]

    logger.info("Embedding %d passages via Remote...", len(docs))
    remote_batches = list(hf_remote.embed_documents(docs))
    remote_passages_vecs = [vec for b in remote_batches for vec in b]

    logger.info("Embedding %d passages via Local...", len(docs))
    local_batches = list(hf_local.embed_documents(docs))
    local_passages_vecs = [vec for b in local_batches for vec in b]

    logger.info("Embedding %d queries via Remote...", len(queries))
    remote_queries_vecs = hf_remote.embed_queries(queries)

    logger.info("Embedding %d queries via Local...", len(queries))
    local_queries_vecs = hf_local.embed_queries(queries)

    assert len(remote_passages_vecs) == len(local_passages_vecs) == len(passages)
    assert len(remote_queries_vecs) == len(local_queries_vecs) == len(queries)

    # 1. Dimensions
    remote_dim = len(remote_passages_vecs[0])
    local_dim = len(local_passages_vecs[0])

    # 2. Vector Math (Cosine & Norms)
    max_diff_norm = 0.0
    min_cosine = 1.0
    total_cosine = 0.0

    for i in range(len(passages)):
        r_norm = l2_norm(remote_passages_vecs[i])
        l_norm = l2_norm(local_passages_vecs[i])
        diff_norm = abs(r_norm - l_norm)
        max_diff_norm = max(max_diff_norm, diff_norm)

        sim = cosine_similarity(remote_passages_vecs[i], local_passages_vecs[i])
        min_cosine = min(min_cosine, sim)
        total_cosine += sim

    for i in range(len(queries)):
        sim = cosine_similarity(remote_queries_vecs[i], local_queries_vecs[i])
        min_cosine = min(min_cosine, sim)
        total_cosine += sim

    mean_cosine = total_cosine / (len(passages) + len(queries))

    # 3. Top-K Agreement
    top1_agreements = []
    top3_agreements = []
    top5_agreements = []

    for i in range(len(queries)):
        rq_vec = remote_queries_vecs[i]
        lq_vec = local_queries_vecs[i]

        r_top = get_top_k(rq_vec, remote_passages_vecs, k=5)
        l_top = get_top_k(lq_vec, local_passages_vecs, k=5)

        top1_agreements.append(compute_agreement(r_top, l_top, 1))
        top3_agreements.append(compute_agreement(r_top, l_top, 3))
        top5_agreements.append(compute_agreement(r_top, l_top, 5))

    avg_top1 = sum(top1_agreements) / len(top1_agreements)
    avg_top3 = sum(top3_agreements) / len(top3_agreements)
    avg_top5 = sum(top5_agreements) / len(top5_agreements)

    print("\n\n" + "=" * 50)
    print("GOLDEN TEST REPORT: HF Remote vs Local E5")
    print("=" * 50)
    print(f"Dimension:        {remote_dim} (HF) / {local_dim} (Local)")
    print(f"Mean Cosine:      {mean_cosine:.6f}")
    print(f"Min Cosine:       {min_cosine:.6f}")
    print(f"Max Norm Dev:     {max_diff_norm:.6f}")
    print("-" * 50)
    print(f"Top-1 Agreement:  {avg_top1:6.2f} %")
    print(f"Top-3 Agreement:  {avg_top3:6.2f} %")
    print(f"Top-5 Agreement:  {avg_top5:6.2f} %")
    print("=" * 50)

    if min_cosine > 0.999:
        print("\n[OK] RECOMMENDATION: Strong mathematical compatibility detected.")
        print("Vectors are virtually identical. You COULD merge vector spaces, but")
        print("keeping HF_E5_REMOTE_768_V1 separated from LOCAL_E5_768_V1 is still")
        print("safer against unannounced provider updates.")
    else:
        print("\n[WARNING] RECOMMENDATION: Mathematical divergence detected.")
        print("Vectors diverge significantly. You MUST use separate vector spaces")
        print("and the `SPACE_CHANGE` provider fallback mechanism.")


if __name__ == "__main__":
    run_golden_test()
