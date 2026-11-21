"""Lightweight Windows/local entry point. Never uses the DATABASE_URL from .env.

Run with backend/.venv/Scripts/python.exe scripts/local.py <command>.
Only the named, labelled Socratia container is accepted; no database discovery.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTAINER = "socratia-local-db"


def container_info():
    result = subprocess.run(
        ["docker", "inspect", CONTAINER], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise SystemExit(
            "No está disponible socratia-local-db. Ejecuta primero scripts/local.py db; no se usará otra base de datos."
        )
    info = json.loads(result.stdout)[0]
    labels = info["Config"].get("Labels") or {}
    bindings = info["HostConfig"].get("PortBindings", {}).get("5432/tcp", [])
    if (
        labels.get("socratia.purpose") != "local-development"
        or not info["Config"]["Image"].startswith("pgvector/pgvector:")
        or bindings != [{"HostIp": "127.0.0.1", "HostPort": "5436"}]
    ):
        raise SystemExit(
            "El contenedor no coincide con la base local autorizada. No se modificó ninguna base."
        )
    return info


def configure():
    from sqlalchemy import URL

    info = container_info()
    if not info["State"]["Running"]:
        raise SystemExit(
            "La base de Socratia está apagada. Ejecuta scripts/local.py db."
        )
    values = dict(item.split("=", 1) for item in info["Config"]["Env"] if "=" in item)
    os.environ["DATABASE_URL"] = URL.create(
        "postgresql+psycopg",
        username=values["POSTGRES_USER"],
        password=values["POSTGRES_PASSWORD"],
        host="127.0.0.1",
        port=5436,
        database=values.get("POSTGRES_DB", values["POSTGRES_USER"]),
    ).render_as_string(hide_password=False)
    os.environ.update(
        VECTOR_PRIMARY_PROVIDER="pgvector",
        LOCAL_TTS_ENABLED="false",
        LOCAL_E5_ENABLED="false",
        LOCAL_QWEN_EMBEDDING_URL="",
        SELF_HOSTED_LLM_URL="",
        COOKIE_SECURE="false",
        FRONTEND_URL="http://localhost:3000",
        CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000",
        LOCAL_STORAGE_PATH=str(ROOT / "backend" / "uploads"),
        PUSH_PRIVATE_KEY="",
        PUSH_PUBLIC_KEY="",
        FCM_SERVICE_ACCOUNT_FILE="",
    )
    sys.path.insert(0, str(ROOT / "backend"))
    os.chdir(ROOT / "backend")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("db", "migrate", "api", "worker", "web", "check")
    )
    command = parser.parse_args().command
    if command == "db":
        result = subprocess.run(
            ["docker", "inspect", CONTAINER], capture_output=True, check=False
        )
        if result.returncode == 0:
            container_info()
            subprocess.run(["docker", "start", CONTAINER], check=True)
        else:
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(ROOT / "compose.local.yaml"),
                    "up",
                    "-d",
                    "db",
                ],
                cwd=ROOT,
                check=True,
            )
        return
    if command == "web":
        environment = {
            **os.environ,
            "NEXT_PUBLIC_API_URL": "http://localhost:8000/api/v1",
        }
        raise SystemExit(
            subprocess.call(
                [
                    "node",
                    "--max-old-space-size=768",
                    "node_modules/next/dist/bin/next",
                    "dev",
                    "--hostname",
                    "127.0.0.1",
                ],
                cwd=ROOT / "frontend",
                env=environment,
            )
        )
    configure()
    if command == "migrate":
        from alembic import command as migration
        from alembic.config import Config

        migration.upgrade(Config("alembic.ini"), "head")
    elif command == "api":
        import uvicorn

        uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
    elif command == "worker":
        from app.cli.preparation_worker import main as worker

        worker()
    else:
        from app.core.database import engine
        from sqlalchemy import text

        with engine.connect() as db:
            print(
                "Base de Socratia: puerto 5436, conexión correcta:",
                db.scalar(text("SELECT 1")) == 1,
            )
        healthy = True
        for url in ("http://127.0.0.1:8000/health", "http://localhost:3000/login"):
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    print(url, response.status)
            except (OSError, ValueError) as exc:
                print(url, type(exc).__name__)
                healthy = False
        if not healthy:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
