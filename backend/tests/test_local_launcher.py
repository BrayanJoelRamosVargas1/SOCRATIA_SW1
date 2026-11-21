"""No Docker changes: local connection guards are tested with synthetic metadata."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

path = Path(__file__).resolve().parents[2] / "scripts/local.py"
spec = importlib.util.spec_from_file_location("socratia_local_launcher", path)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.mark.parametrize(
    "image,labels,bindings",
    [
        (
            "postgres:17",
            {"socratia.purpose": "local-development"},
            [{"HostIp": "127.0.0.1", "HostPort": "5436"}],
        ),
        ("pgvector/pgvector:pg17", {}, [{"HostIp": "127.0.0.1", "HostPort": "5436"}]),
        (
            "pgvector/pgvector:pg17",
            {"socratia.purpose": "local-development"},
            [{"HostIp": "", "HostPort": "5435"}],
        ),
    ],
)
def test_refuses_other_project_databases(monkeypatch, image, labels, bindings):
    info = {
        "Config": {"Image": image, "Labels": labels},
        "HostConfig": {"PortBindings": {"5432/tcp": bindings}},
    }
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout=json.dumps([info])))
    monkeypatch.setattr(launcher.subprocess, "run", run)
    with pytest.raises(SystemExit, match="no coincide"):
        launcher.container_info()
    assert run.call_count == 1 and run.call_args.args[0][:2] == ["docker", "inspect"]


def test_missing_socratia_database_never_falls_back_to_dotenv(monkeypatch):
    monkeypatch.setattr(
        launcher.subprocess, "run", Mock(return_value=SimpleNamespace(returncode=1))
    )
    with pytest.raises(SystemExit, match="no se usará otra base"):
        launcher.container_info()
