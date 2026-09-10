import argparse
import logging
import os
import sys

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("preload_embeddings")


def main():
    parser = argparse.ArgumentParser(description="Preload embedding model for LocalE5Provider")
    parser.add_argument(
        "--model", type=str, help="Model name to preload (defaults to config E5_EMBEDDING_MODEL)"
    )
    parser.add_argument(
        "--revision",
        type=str,
        default="d128750597153bb5987e10b1c3493a34e5a4502a",
        help="Model revision SHA",
    )
    parser.add_argument("--force", action="store_true", help="Force redownload even if cached")
    parser.add_argument(
        "--offline-check",
        action="store_true",
        help="Verify that the model can be loaded strictly offline",
    )
    args = parser.parse_args()

    settings = get_settings()
    model_name = args.model or settings.e5_embedding_model
    model_revision = args.revision

    if args.offline_check:
        logger.info("Modo: OFFLINE CHECK")
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        local_only = True
    else:
        logger.info("Modo: PRELOAD ONLINE")
        if "HF_HUB_OFFLINE" in os.environ:
            del os.environ["HF_HUB_OFFLINE"]
        if "TRANSFORMERS_OFFLINE" in os.environ:
            del os.environ["TRANSFORMERS_OFFLINE"]
        local_only = False

    try:
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error(
            "sentence-transformers/huggingface_hub no estan instalados. "
            "Please install it using: pip install -r requirements-local-embeddings.txt"
        )
        sys.exit(1)

    logger.info("Local E5 preflight")
    logger.info("──────────────────────────")
    try:
        if not local_only:
            logger.info(f"Downloading snapshot for {model_name} @ {model_revision}")
            snapshot_download(repo_id=model_name, revision=model_revision, local_files_only=False)
            logger.info("Download complete.")

        # Load the model with specific revision
        model = SentenceTransformer(
            model_name, revision=model_revision, local_files_only=local_only
        )
        logger.info("model          ✅")
        logger.info("revision       ✅")

        # Verify dimension
        dim = model.get_sentence_embedding_dimension()
        if dim == 768:
            logger.info("dimension 768  ✅")
        else:
            logger.error("dimension 768  ❌ (got %d)", dim)
            sys.exit(1)

        logger.info("tokenizer      ✅")

        # Test inference
        res = model.encode(["passage: test text"], normalize_embeddings=True)
        if len(res) == 1 and len(res[0]) == 768:
            logger.info("test embedding ✅")
        else:
            logger.error("test embedding ❌")
            sys.exit(1)

        if not local_only:
            logger.info("Preload online complete. Local E5 is ready for offline use.")
        else:
            logger.info("Offline check complete. Model loaded successfully from cache.")

    except Exception:
        logger.exception("Failed to load/preload model %s", model_name)
        sys.exit(1)


if __name__ == "__main__":
    main()
