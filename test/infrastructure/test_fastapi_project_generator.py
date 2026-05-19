import pathlib

import yaml

from microforge.domain.spec.models import SpecV1
from microforge.infrastructure.outbound.generation.fastapi_project_generator import (
    FastApiProjectGenerator,
)


def _load_spec(path: str) -> SpecV1:
    with pathlib.Path(path).open("r", encoding="utf-8") as handle:
        return SpecV1.model_validate(yaml.safe_load(handle))


def test_fastapi_project_generator_creates_minimal_project_files() -> None:
    spec = _load_spec("examples/spec_valid.yaml")
    files = FastApiProjectGenerator().generate(spec)

    by_path = {project_file.path: project_file.content.decode("utf-8") for project_file in files}

    assert set(by_path) == {"README.md", "pyproject.toml", "src/main.py"}
    assert "# orders" in by_path["README.md"]
    assert 'name = "orders"' in by_path["pyproject.toml"]
    assert 'app = FastAPI(title="orders API")' in by_path["src/main.py"]
    assert '@app.get("/api/v1/health")' in by_path["src/main.py"]
