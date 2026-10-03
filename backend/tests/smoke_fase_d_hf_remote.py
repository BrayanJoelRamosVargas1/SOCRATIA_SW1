import logging
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingDocument
from app.integrations.embeddings.huggingface_e5 import HuggingFaceE5Provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fase_d_hf_remote")


def run_test():
    settings = get_settings()

    hf_key_obj = settings.huggingface_api_key
    hf_key = (
        hf_key_obj.get_secret_value() if hasattr(hf_key_obj, "get_secret_value") else hf_key_obj
    )
    if not hf_key or hf_key == "YOUR_NEW_HUGGINGFACE_KEY_HERE":
        logger.error("HUGGINGFACE_API_KEY no configurado en el entorno (.env).")
        logger.error("Este test requiere una clave real con permiso 'Inference Providers'.")
        sys.exit(1)

    logger.info("Verificando que api-inference.huggingface.co no este hardcodeado...")
    with open(
        os.path.join(os.path.dirname(__file__), "../app/integrations/embeddings/huggingface_e5.py")
    ) as f:
        content = f.read()
        # Ensure it doesn't try to post to the legacy domain
        if "https://api-inference.huggingface.co" in content:
            logger.error("ERROR: Encontramos el hostname legacy hardcodeado en huggingface_e5.py!")
            sys.exit(1)

    provider = HuggingFaceE5Provider(
        api_key=hf_key, model="intfloat/multilingual-e5-base", dimensions=768
    )

    logger.info("Probando is_available...")
    if not provider.is_available:
        logger.error("Provider reporta indisponibilidad. Verifica los permisos de tu token.")
        sys.exit(1)

    logger.info("Provider available. Probando embed_documents...")
    docs = [
        EmbeddingDocument(
            title="",
            text="Este es un documento de prueba para probar la API moderna de Inference Providers.",
        ),
        EmbeddingDocument(
            title="",
            text="El segundo documento es ligeramente mas largo y habla sobre bases de datos vectoriales en la nube.",
        ),
    ]

    try:
        batches = list(provider.embed_documents(docs))
        vectors = batches[0]

        logger.info("Provider: %s", provider.provider_id)
        logger.info("Model: %s", provider.model)
        logger.info("Dimension: %s", provider.dimensions)
        logger.info("Vectors: %d", len(vectors))

        if len(vectors) == 2 and len(vectors[0]) == provider.dimensions:
            logger.info("PASS: Validacion de API HF Inference completada con exito.")
        else:
            logger.error(
                "FAILED: Dimensiones de vectores incorrectas o cantidad de vectores no coincide."
            )
            sys.exit(1)
    except Exception as e:
        logger.error("Error durante la generacion de embeddings: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    run_test()
