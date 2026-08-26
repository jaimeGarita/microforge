from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from microforge.domain.spec.models import SpecV1
from microforge.domain.spec.semantics import validate_semantics
from microforge.infrastructure.outbound.generation.targets.python.fastapi.generator import (
    PythonFastApiProjectGenerator,
)


def test_generated_project_starts_and_serves_routes(tmp_path: Path) -> None:
    spec = SpecV1.model_validate(
        {
            "project": {"packageName": "runtime_service"},
            "service": {"name": "runtime"},
            "api": {
                "basePath": "/api/v1",
                "endpoints": [
                    {
                        "name": "listItems",
                        "model": "Item",
                        "path": "/items",
                        "method": "GET",
                    }
                ],
            },
            "models": [
                {
                    "name": "Item",
                    "fields": [
                        {"name": "id", "type": "int", "primaryKey": True},
                        {"name": "name", "type": "string"},
                    ],
                }
            ],
        }
    )
    validate_semantics(spec)

    for project_file in PythonFastApiProjectGenerator().generate(spec):
        destination = tmp_path / project_file.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(project_file.content)

    script = """
from fastapi.testclient import TestClient
from runtime_service.main import app

with TestClient(app) as client:
    health = client.get('/api/v1/health')
    assert health.status_code == 200, health.text
    assert health.json() == {'status': 'ok'}
    items = client.get('/api/v1/items')
    assert items.status_code == 200, items.text
    assert items.json() == []
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(tmp_path / "src")
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
