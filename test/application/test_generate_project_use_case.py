import pathlib

import pytest
import yaml

from microforge.application.generation.ports.outbound import (
    ProjectGeneratorPort,
    ProjectPackagerPort,
)
from microforge.application.generation.use_cases.generate_project import GenerateProjectUseCase
from microforge.application.spec.ports.outbound import SpecLoaderPort
from microforge.domain.generation.project_file import ProjectFile
from microforge.domain.spec.errors import SpecValidationErrors
from microforge.domain.spec.models import SpecV1


class InMemoryLoader(SpecLoaderPort):
    def __init__(self, raw: dict):
        self.raw = raw

    def load_bytes(self, data: bytes) -> SpecV1:
        del data
        return SpecV1.model_validate(self.raw)


class StaticGenerator(ProjectGeneratorPort):
    def generate(self, spec: SpecV1) -> list[ProjectFile]:
        return [ProjectFile(path="README.md", content=spec.service.name.encode("utf-8"))]


class RecordingPackager(ProjectPackagerPort):
    def __init__(self):
        self.files: list[ProjectFile] = []

    def package(self, files: list[ProjectFile]) -> bytes:
        self.files = files
        return b"zip-bytes"


def _load_yaml(path: str) -> dict:
    with pathlib.Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_generate_project_use_case_returns_packaged_project() -> None:
    packager = RecordingPackager()
    service = GenerateProjectUseCase(
        spec_loader=InMemoryLoader(_load_yaml("examples/spec_valid.yaml")),
        generator=StaticGenerator(),
        packager=packager,
    )

    result = service.run_bytes(b"unused")

    assert result == b"zip-bytes"
    assert packager.files == [ProjectFile(path="README.md", content=b"orders")]


def test_generate_project_use_case_reports_semantic_errors() -> None:
    service = GenerateProjectUseCase(
        spec_loader=InMemoryLoader(_load_yaml("examples/spec_invalid.yaml")),
        generator=StaticGenerator(),
        packager=RecordingPackager(),
    )

    with pytest.raises(SpecValidationErrors):
        service.run_bytes(b"unused")
